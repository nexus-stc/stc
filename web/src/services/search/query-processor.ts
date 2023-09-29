interface QueryConfig {
  page: number
  page_size?: number
  fields?: string[]
  index_name?: string
  language?: string
  is_date_sorting_enabled: boolean
  random?: boolean
  type?: Type,
  timerange: [number, number]
}

export enum Type {
  Books = "📚 Books",
}

export enum Language {
  en = '🇬🇧 English',
  ar = '🇦🇪 Arabic',
  pb = '🇧🇷 Brazilian Portuguese',
  zh = '🇨🇳 Chinese',
  am = '🇪🇹 Ethiopian',
  fa = '🇮🇷 Farsi',
  de = '🇩🇪 German',
  hi = '🇮🇳 Hindi',
  id = '🇮🇩 Indonesian',
  it = '🇮🇹 Italian',
  ja = '🇯🇵 Japanese',
  ms = '🇲🇾 Malay',
  ru = '🇷🇺 Russian',
  es = '🇪🇸 Spanish',
  tg = '🇹🇯 Tajik',
  uk = '🇺🇦 Ukrainian',
  uz = '🇺🇿 Uzbek'
}

export class QueryProcessor {
  generate_request (index_config: object, query: string, query_config: QueryConfig) {
    return {
      index_alias: index_config.index_name,
      query: default_queries(
        query,
        query_config,
      ),
      collectors: default_collectors(query_config),
      is_fieldnorms_scoring_enabled: false,
      use_cache: true,
      load_cache: true
    }
  }
}

export function default_queries (
  query: string,
  options: QueryConfig,
) {
  let structured_query = { query: { all: { } } }
  if (query) {
    structured_query = { query: { match: { value: query } } }
  }
  if ((options.language || options.type || options.timerange)) {
    let subqueries = [];
    if (query) {
      subqueries = [{
        query: { query: structured_query.query },
        occur: 1
      }]
    }
    if (options.language) {
      subqueries.push({
        query: { query: { term: { field: 'languages', value: options.language} } },
        occur: 1
      })
    }
    if (options.type === "Books") {
      subqueries.push({
        query: { query: { boolean: { subqueries: [
          { occur: 0, query: { query: { term: { field: "type", value: "book" } }}},
          { occur: 0, query: { query: { term: { field: "type", value: "edited-book" } }}},
          { occur: 0, query: { query: { term: { field: "type", value: "monograph" } }}},
          { occur: 0, query: { query: { term: { field: "type", value: "reference-book" } }}},
        ]}}},
        occur: 1,
      })
    }
    if (options.timerange) {
      subqueries.push({
        query: { query: { range: { field: 'issued_at', value: {
          left: options.timerange[0].toString(), including_left: true,
          right: options.timerange[1].toString(), including_right: false,
        }} } },
        occur: 1
      })
    }
    structured_query = {
      query: {
        boolean: {
          subqueries: subqueries
        }
      }
    }
  }
  return structured_query
}

export function default_collectors (
  query_config: QueryConfig,
) {
  const page_size = query_config.page_size ?? 5
  if (query_config.random) {
    return [{ collector: { reservoir_sampling: { limit: query_config.page_size } } }, { collector: { count: {} } }]
  }
  return [{
      collector: {
        top_docs: {
          offset: (query_config.page - 1) * page_size,
          limit: page_size,
          snippet_configs: { abstract: 400, title: 180 },
          fields: (query_config.fields != null) || [],
          scorer: query_config.is_date_sorting_enabled
            ? { scorer: { order_by: 'issued_at' } }
            : null
        }
      }
    },
  { collector: { count: {} } }]
}
