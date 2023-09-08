// @ts-nocheck

import {
  type IndexQuery,
} from 'summa-wasm'

import { type SearchService } from "./search-service";

export class LocalSearchService implements SearchService {
  constructor () {}
  async setup () {}
  async search (index_query: IndexQuery): Promise<object[]> {

  }
}
