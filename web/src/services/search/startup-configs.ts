import { seeds, summa } from 'summa-wasm'

export async function get_startup_configs () {
  let ipfs_base_path = window.location.pathname ?? ''
  if (!ipfs_base_path.endsWith('/')) {
    ipfs_base_path += '/'
  }
  return [
    {
      index_name: 'nexus_free',
      seed: new seeds.LocalDatabaseSeed(
          `${ipfs_base_path}data/nexus_free`,
          new summa.proto.CacheConfig({ cache_size: 128 * 1024 * 1024 })
      ),
      is_enabled: true,
      query_parser_config: {
        field_aliases: {
          author: 'authors.name',
          authors: 'authors.name',
          cid: 'links.cid',
          extension: 'links.extension',
          format: 'links.extension',
          isbns: 'id.isbns',
          issns: 'metadata.issns',
          lang: 'language',
          pub: 'metadata.publisher',
          ser: 'metadata.series'
        },
        field_boosts: {
          title: 1.3
        },
        term_field_mapper_configs: {
          doi_isbn: { fields: ['id.isbns'] },
          isbn: { fields: ['id.isbns'] }
        },
        term_limit: 10,
        default_fields: ['abstract', 'content', 'title'],
        exact_matches_promoter: {
          slop: 0,
          boost: 1.5,
          fields: ['title']
        },
        removed_fields: ['concepts', 'doi', 'ev', 'rd']
      },
      is_exact_matches_promoted: true,
      is_fieldnorms_scoring_enabled: false,
      is_temporal_scoring_enabled: false
    },
    {
      index_name: 'nexus_media',
      seed: new seeds.LocalDatabaseSeed(
          `${ipfs_base_path}data/nexus_media`,
          new summa.proto.CacheConfig({ cache_size: 128 * 1024 * 1024 })
      ),
      query_parser_config: {
        field_aliases: {
          lang: 'language'
        },
        field_boosts: {
          title: 1.3
        },
        term_field_mapper_configs: {},
        term_limit: 10,
        default_fields: ['title'],
        exact_matches_promoter: {
          slop: 0,
          boost: 1.5,
          fields: ['title']
        },
        removed_fields: []
      },
      is_enabled: false,
      is_fieldnorms_scoring_enabled: false,
      is_temporal_scoring_enabled: false
    },
    {
      index_name: 'nexus_science',
      seed: new seeds.LocalDatabaseSeed(
          `${ipfs_base_path}data/nexus_science`,
          new summa.proto.CacheConfig({ cache_size: 512 * 1024 * 1024 })
      ),
      query_parser_config: {
        field_aliases: {
          author: 'authors.family',
          authors: 'authors.family',
          cid: 'links.cid',
          extension: 'links.extension',
          format: 'links.extension',
          isbns: 'id.isbns',
          issns: 'metadata.issns',
          lang: 'language',
          ev: 'metadata.event.name',
          pub: 'metadata.publisher',
          ser: 'metadata.series'
        },
        field_boosts: {
          title: 1.3
        },
        term_field_mapper_configs: {
          doi: { fields: ['doi'] },
          doi_isbn: { fields: ['metadata.isbns'] },
          isbn: { fields: ['metadata.isbns'] }
        },
        term_limit: 10,
        default_fields: ['abstract', 'content', 'title'],
        exact_matches_promoter: {
          slop: 0,
          boost: 1.5,
          fields: ['title']
        },
        removed_fields: ['id']
      },
      is_enabled: true,
      is_fieldnorms_scoring_enabled: false,
      is_temporal_scoring_enabled: false
    }
  ]
}
