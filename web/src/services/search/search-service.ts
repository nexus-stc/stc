// @ts-nocheck

import {
  type IndexQuery,
} from 'summa-wasm'

export interface SearchService {
  setup (): Promise<void>;
  search (index_query: IndexQuery): Promise<object[]>;
}
