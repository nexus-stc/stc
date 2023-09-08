// @ts-nocheck

import {
  type IndexQuery,
  type IndexRegistryOptions,
  RemoteIndexRegistry,
  seeds, summa
} from 'summa-wasm'
import { ref, toRaw } from 'vue'

import { tracked_download } from '@/components/download-progress'
import { type SearchService } from "./search-service";
import { QueryProcessor } from "@/services/search/query-processor";

export function get_index_config () {
  let ipfs_base_path = window.location.pathname ?? ''
  if (!ipfs_base_path.endsWith('/')) {
    ipfs_base_path += '/'
  }
  return {
      index_name: 'nexus_science',
      seed: new seeds.LocalDatabaseSeed(
          `${ipfs_base_path}data`,
          new summa.proto.CacheConfig({ cache_size: 512 * 1024 * 1024 })
      ),
      query_parser_config: {
        field_aliases: {
          author: 'authors.family',
          authors: 'authors.family',
          cid: 'links.cid',
          doi: 'id.dois',
          extension: 'links.extension',
          format: 'links.extension',
          isbn: 'metadata.isbns',
          isbns: 'metadata.isbns',
          issns: 'metadata.issns',
          lang: 'languages',
          lid: 'id.libgen_ids',
          ev: 'metadata.event.name',
          pub: 'metadata.publisher',
          rd: 'references.doi',
          ser: 'metadata.series',
          zid: 'id.zlibrary_ids',
        },
        field_boosts: {
          authors: 2.7,
          title: 2.0
        },
        term_field_mapper_configs: {
          doi: { fields: ['id.dois'] },
          doi_isbn: { fields: ['metadata.isbns'] },
          isbn: { fields: ['metadata.isbns'] }
        },
        term_limit: 10,
        default_fields: ['abstract', 'content', 'title'],
        exact_matches_promoter: {
          slop: 1,
          boost: 1.5,
          fields: ['title']
        },
      },
      is_exact_matches_promoted: false,
    }
}


export class IpfsSearchService implements SearchService {
  init_guard: Promise<void>
  current_init_status: any
  remote_index_registry: RemoteIndexRegistry
  index_config: any
  query_processor: QueryProcessor

  constructor (registry_options?: IndexRegistryOptions) {
    const worker_url = new URL(
      '~/summa-wasm/dist/root-worker.js',
      import.meta.url
    )
    const wasm_url = new URL(
      '~/summa-wasm/dist/index_bg.wasm',
      import.meta.url
    )
    this.current_init_status = ref('')
    tracked_download([wasm_url], this.current_init_status)

    this.index_config = get_index_config();
    this.query_processor = new QueryProcessor();
    this.remote_index_registry = new RemoteIndexRegistry(
      worker_url,
      wasm_url,
      registry_options
    )
    this.init_guard = (async () => {
      await this.remote_index_registry.init_guard
      await this.setup()
    })()
  }

  async setup () {
    try {
      const rc = await this.index_config.seed.retrieve_remote_engine_config()
      const meta_response = await fetch(rc.url_template.replace('{file_name}', 'meta.json'))
      const meta = await meta_response.json()
      const files = []
      for (const segment of meta.segments) {
        if (segment.deletes) {
          files.push(rc.url_template.replace('{file_name}', segment.segment_id.replace(/-/g, '') + '.' + segment.deletes.opstamp + '.del'))
        }
      }
      files.push(rc.url_template.replace('{file_name}', 'hotcache.' + meta.opstamp + '.bin'))
      await tracked_download(files, this.current_init_status);
      await this.add_index(this.index_config);
    } catch (e) {
      console.error('Dropping stored data due to error: ', e)
      throw e
    }
  }

  async add_index (index_config: {
    index_name: string
    seed: seeds.IIndexSeed
    query_parser_config: any
  }): Promise<Object> {
    const remote_engine_config =
      await index_config.seed.retrieve_remote_engine_config()
    await this.remote_index_registry.add(index_config.index_name, {
      config: { remote: remote_engine_config },
      query_parser_config: toRaw(index_config.query_parser_config)
    })
  }

  async search (index_query: IndexQuery) {
    await this.init_guard
    return await this.remote_index_registry.search(index_query)
  }

  async custom_search (
    query: string,
    options: QueryOptions,
  ) {
    const search_query = this.query_processor.generate_request(this.index_config, query, options)
    return await this.search(search_query)
  }
}
