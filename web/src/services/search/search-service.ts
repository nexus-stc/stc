// @ts-nocheck

import {
    type IndexQuery,
} from 'summa-wasm'
import {
    IpfsSearchProvider,
    RemoteSearchProvider,
    type SearchProvider, SearchProviderStatus,
} from "@/services/search/search-provider";
import {ref} from "vue";

export class SearchService {
    search_providers: Array<SearchProvider>;
    current_provider_ix: Number;
    init_guard: Promise<void>;
    current_init_status: any;
    loading_failure_reason: any;


    constructor(logging_level: string) {
        this.current_init_status = ref(undefined);
        this.search_providers = [
            new RemoteSearchProvider(
                "https://api.standard-template-construct.org",
                "Nebula Nomad Station",
            ),
            new IpfsSearchProvider(this.current_init_status, {logging_level}),
        ];
        this.current_provider_ix = ref(undefined);
        this.loading_failure_reason = ref(undefined);
        this.init_guard = (async () => {
            await this.setup();
        })()
    }

    async setup() {
        let last_error = undefined;
        for (const [index, search_provider] of this.search_providers.entries()) {
            try {
                await search_provider.setup(this.current_init_status);
            } catch (e) {
                last_error = e;
                continue;
            }
            if (search_provider.status.value == SearchProviderStatus.Succeeded) {
                this.current_provider_ix.value = index;
                return;
            }
        }
        if (last_error !== undefined) {
            this.loading_failure_reason.value = last_error.toString();
        }
    }

    async change_provider(index: Number) {
        const new_provider = this.search_providers[index];
        if (new_provider.status.value == SearchProviderStatus.NotSetup) {
            await new_provider.setup();
        } else {
            await new_provider.healthcheck();
        }
        if (new_provider.status.value == SearchProviderStatus.Succeeded) {
            this.current_provider_ix.value = index;
        }
    }

    async search(index_query: IndexQuery, options: QueryOptions): Promise<object[]> {
      await this.init_guard;
      return this.search_providers[this.current_provider_ix.value].search(index_query, options);
    }
}
