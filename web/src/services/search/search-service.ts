import {
  IndexConfig,
  IndexQuery,
  seeds,
  RemoteIndexRegistry,
  IndexRegistryOptions,
} from "summa-wasm";
import { toRaw, ref } from "vue";
import { meta_db, SearchMetric, user_db } from "@/database";
import { default_collectors, default_queries } from "./default";
import { get_startup_configs } from "./startup-configs";
import { tracked_download } from "../../components/download-progress";

type Options = {
  page: number;
  page_size?: number;
  fields?: string[];
  index_name?: string;
  language?: string;
  date_sorting: boolean;
};

export class SearchService {
  init_guard: Promise<void>;
  current_init_status: any;
  remote_index_registry: RemoteIndexRegistry;

  constructor(options?: IndexRegistryOptions) {
    const worker_url = new URL(
      "~/summa-wasm/dist/root-worker.js",
      import.meta.url
    );
    const wasm_url = new URL(
      "~/summa-wasm/dist/index_bg.wasm",
      import.meta.url
    );
    this.current_init_status = ref("");
    tracked_download([wasm_url], this.current_init_status);

    this.remote_index_registry = new RemoteIndexRegistry(
      worker_url,
      wasm_url,
      options
    );
    this.init_guard = (async () => {
      await this.remote_index_registry.init_guard;
      return await this.setup();
    })();
  }

  async setup() {
    try {
      await this.load_from_store();
      if (await this.is_empty()) {
        await this.install_defaults();
      }
    } catch (e) {
      console.error("Dropping stored data due to error: ", e);
      await meta_db.index_configs.clear();
      throw e;
    }
  }

  async load_from_store() {
    const index_configs = await meta_db.index_configs.toArray();
    const loading_futures = index_configs.map((index_config) =>
      (async () => {
        const remote_engine_config = toRaw(index_config.remote_engine_config);
        await this.remote_index_registry.add(index_config.index_name,{
          config: { remote: remote_engine_config },
          query_parser_config: toRaw(index_config.query_parser_config),
        });
        await this.remote_index_registry.warmup(index_config.index_name);
      })()
    );
    return await Promise.all(loading_futures);
  }
  async add_index(startup_config: {
    index_name: string,
    seed: seeds.IIndexSeed;
    query_parser_config: any,
    is_enabled: boolean;
    is_fieldnorms_scoring_enabled: boolean;
    is_temporal_scoring_enabled: boolean;
  }): Promise<Object> {
    const remote_engine_config =
      await startup_config.seed.retrieve_remote_engine_config();
    const index_attributes = await this.remote_index_registry.add(startup_config.index_name, {
      config: { remote: remote_engine_config },
      query_parser_config: toRaw(startup_config.query_parser_config)
    });
    const index_properties = {
      is_enabled: startup_config.is_enabled,
      is_fieldnorms_scoring_enabled: startup_config.is_fieldnorms_scoring_enabled,
      is_temporal_scoring_enabled: startup_config.is_temporal_scoring_enabled,
    };
    const index_config = new IndexConfig(
      startup_config.index_name,
      index_attributes.description!,
      Number(index_attributes.created_at) as number,
      startup_config.seed,
      remote_engine_config,
      startup_config.query_parser_config,
      index_properties,
    );
    await meta_db.save(toRaw(index_config));
    return index_config;
  }
  async search(index_queries: IndexQuery[]) {
    return this.remote_index_registry.search(index_queries);
  }

  async is_empty() {
    const count = await meta_db.index_configs.count();
    return count < 3;
  }
  async install_defaults() {
    const startup_configs = await get_startup_configs();
    const files = await Promise.all(
      startup_configs.map((c) =>
        (async () => {
          const rc = await c.seed.retrieve_remote_engine_config();
          const meta_response = await fetch(rc.url_template.replace("{file_name}", "meta.json"))
          const meta = await meta_response.json();
          let files = []
          for (let segment of meta.segments) {
            if (segment.deletes) {
              files.push(rc.url_template.replace("{file_name}", segment.segment_id.replace(/-/g, "") + "." + segment.deletes.opstamp + ".del"));
            }
          }
          files.push(rc.url_template.replace("{file_name}", "hotcache." + meta.opstamp + ".bin"));
          return files;
        })()
      )
    );
    await tracked_download(files.flat(), this.current_init_status);
    await Promise.all(
      startup_configs.map((startup_config) =>
        (async () => {
          await this.add_index(startup_config);
        })()
      )
    );
  }
  async get_enabled_index_configs(index_name?: string) {
    await this.init_guard;
    return meta_db.index_configs
      .filter(
        (index_config) =>
          index_config.index_properties.is_enabled &&
          (index_name === undefined || index_name === index_config.index_name)
      )
      .toArray();
  }
  generate_request(index_config: IndexConfig, query: string, options: Options) {
    return {
      index_alias: index_config.index_name,
      query: default_queries(
        index_config.index_name,
        query,
        options.language
      ),
      collectors: default_collectors(index_config.index_name, {
        page: options.page,
        page_size: options.page_size,
        fields: options.fields,
        is_date_sorting_enabled: options.date_sorting,
        is_temporal_scoring_enabled:
          index_config.index_properties.is_temporal_scoring_enabled,
      }),
      is_fieldnorms_scoring_enabled:
        index_config.index_properties.is_fieldnorms_scoring_enabled,
    };
  }
  async custom_search(
    query: string,
    options: Options,
    update_search_metrics?: boolean
  ) {
    await this.init_guard;
    const enabled_index_configs = await this.get_enabled_index_configs(
      options.index_name
    );
    const start_time = performance.now();
    const search_queries = enabled_index_configs.map((index_config) => {
      return this.generate_request(index_config, query, options);
    });
    const results = await this.search(search_queries);
    const spent = performance.now() - start_time;
    if (update_search_metrics) {
      user_db.add_search_metrics(new SearchMetric(spent));
    }
    return results;
  }

  async random_search(
    options: Options,
  ) {
    await this.init_guard;
    const enabled_index_configs = await this.get_enabled_index_configs(
      options.index_name
    );
    const search_queries = enabled_index_configs.map((index_config) => {
      return {
        index_alias: index_config.index_name,
        query: { query: {all: {}}},
        collectors: [{ collector: { reservoir_sampling: { limit: options.page_size } } }],
        is_fieldnorms_scoring_enabled: false,
      }
    });
    return await this.search(search_queries);
  }
}
