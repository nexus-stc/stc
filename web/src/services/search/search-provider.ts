import {grpc_web, IndexQuery, IndexRegistryOptions, RemoteIndexRegistry, seeds} from "summa-wasm";
import {tracked_download} from "@/components/download-progress";
import {ref, toRaw} from "vue";
import {QueryProcessor} from "@/services/search/query-processor";
import {GrpcWebFetchTransport} from "@protobuf-ts/grpcweb-transport";

export function get_index_config() {
    let ipfs_base_path = window.location.pathname ?? ''
    if (!ipfs_base_path.endsWith('/')) {
        ipfs_base_path += '/'
    }
    return {
        index_name: 'nexus_science',
        seed: new seeds.LocalDatabaseSeed(
            `${ipfs_base_path}data`,
            grpc_web.index_service.CacheConfig.create({cache_size: 512 * 1024 * 1024})
        ),
        query_parser_config: {
            field_aliases: {
                ark_id: 'id.ark_ids',
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
                ev: 'metadata.event.name',
                nexus_id: 'id.nexus_id',
                pmid: 'id.pubmed_id',
                pub: 'metadata.publisher',
                pubmed_id: 'id.pubmed_id',
                rd: 'references.doi',
                ser: 'metadata.series',
            },
            field_boosts: {
                authors: 2.7,
                title: 2.0
            },
            term_field_mapper_configs: {
                doi: {fields: ['id.dois']},
                doi_isbn: {fields: ['metadata.isbns']},
                isbn: {fields: ['metadata.isbns']}
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

export enum SearchProviderStatus {
  NotSetup = 0,
  NotChecked = 1,
  Checking,
  Failed,
  Succeeded,
}

export interface SearchProvider {
    setup(): Promise<void>;

    healthcheck(): Promise<void>;

    search(index_query: IndexQuery, options: QueryOptions): Promise<object[]>;
}

const wasm_url = new URL(
    '~/summa-wasm/dist/index_bg.wasm',
    import.meta.url
)

export class IpfsSearchProvider implements SearchProvider {
    init_guard: Promise<void>;
    remote_index_registry: RemoteIndexRegistry;
    index_config: any;
    query_processor: QueryProcessor;
    name: string;
    status: Ref<UnwrapRef<SearchProviderStatus>>;
    current_init_status: any;
    registry_options?: IndexRegistryOptions;
    page_size: number;

    constructor(current_init_status, registry_options?: IndexRegistryOptions) {
        this.current_init_status = current_init_status
        this.registry_options = registry_options
        this.index_config = get_index_config();
        this.query_processor = new QueryProcessor();
        this.name = "IPFS";
        this.status = ref(SearchProviderStatus.NotSetup);
        this.page_size = 5;
    }

    async setup() {
        if (this.init_guard) {
            return await this.init_guard;
        }
        this.init_guard = (async () => {
            const worker_url = new URL(
                '~/summa-wasm/dist/root-worker.js',
                import.meta.url
            )
            this.remote_index_registry = new RemoteIndexRegistry(
                worker_url,
                wasm_url,
                this.registry_options
            )
            await this.remote_index_registry.init_guard
            await this.inner_setup()
        })()
        return await this.init_guard;
    }

    async inner_setup() {
        try {
            await tracked_download([wasm_url], this.current_init_status);
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
            this.status.value = SearchProviderStatus.NotChecked;
            this.current_init_status.value = undefined;
            await this.healthcheck();
        } catch (e) {
            console.error('Dropping stored data due to error: ', e)
            throw e
        }
    }

    async add_index(index_config: {
        index_name: string
        seed: seeds.IIndexSeed
        query_parser_config: any
    }): Promise<Object> {
        const remote_engine_config =
            await index_config.seed.retrieve_remote_engine_config()
        return await this.remote_index_registry.add(index_config.index_name, {
            config: {remote: remote_engine_config},
            query_parser_config: toRaw(index_config.query_parser_config)
        })
    }

    async search(index_query: IndexQuery, options: QueryOptions) {
        await this.init_guard
        options.page_size = options.page_size ?? this.page_size;
        const parsed_index_query = this.query_processor.generate_request(this.index_config, index_query, options)
        return await this.remote_index_registry.search_by_binary_proto(grpc_web.query.SearchRequest.toBinary(grpc_web.query.SearchRequest.fromJson(parsed_index_query)))
    }

    async healthcheck(): Promise<void> {
        this.status.value = SearchProviderStatus.Succeeded;
    }
}

export class RemoteSearchProvider implements SearchProvider {
    search_api: grpc_web.public_service_client.PublicApiClient;
    index_config: Object;
    name: string;
    query_processor: QueryProcessor;
    status: Ref<UnwrapRef<SearchProviderStatus>>;
    page_size: number;

    constructor(base_url: string, name: string) {
        let transport = new GrpcWebFetchTransport({
            baseUrl: base_url,
            format: "binary",
        });
        this.search_api = new grpc_web.public_service_client.PublicApiClient(transport);
        this.index_config = get_index_config();
        this.name = name;
        this.query_processor = new QueryProcessor();
        this.status = ref(SearchProviderStatus.NotSetup);
        this.page_size = 10;
    }

    async setup() {
        await this.healthcheck();
    }

    async search(index_query: IndexQuery, options: QueryOptions): Promise<object[]> {
        options.page_size = options.page_size ?? this.page_size;
        options.query_parser_config = this.index_config.query_parser_config;
        const parsed_index_query = this.query_processor.generate_request(this.index_config, index_query, options);
        let { response } = await this.search_api.search(grpc_web.query.SearchRequest.fromJson(parsed_index_query));
        return response.collector_outputs
    }

    async healthcheck(): Promise<void> {
        try {
            this.status.value = SearchProviderStatus.Checking;
            await this.search_api.search(grpc_web.query.SearchRequest.fromJson({"index_alias": "nexus_science", "query": {"empty": {}}}));
            this.status.value = SearchProviderStatus.Succeeded;
        } catch(e) {
            this.status.value = SearchProviderStatus.Failed;
        }
    }
}