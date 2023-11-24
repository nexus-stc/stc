import { grpc_web } from "summa-wasm";

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
    query_parser_config: grpc_web.query.QueryParserConfig,
}

export enum Type {
    Books = "📚 Books",
}

export enum Language {
    en = '🇬🇧 English',
    ar = '🇦🇪 Arabic',
    zh = '🇨🇳 Chinese',
    am = '🇪🇹 Ethiopian',
    fa = '🇮🇷 Farsi',
    de = '🇩🇪 German',
    hi = '🇮🇳 Hindi',
    id = '🇮🇩 Indonesian',
    it = '🇮🇹 Italian',
    ja = '🇯🇵 Japanese',
    ms = '🇲🇾 Malay',
    pt = '🇧🇷 Portuguese',
    ru = '🇷🇺 Russian',
    es = '🇪🇸 Spanish',
    tg = '🇹🇯 Tajik',
    uk = '🇺🇦 Ukrainian',
    uz = '🇺🇿 Uzbek'
}

export class QueryProcessor {
    generate_request(index_config: object, query: string, query_config: QueryConfig) {
        return {
            index_alias: index_config.index_name,
            query: default_queries(
                query,
                query_config,
            ),
            collectors: default_collectors(query_config),
            is_fieldnorms_scoring_enabled: false,
            store_cache: true,
            load_cache: true
        }
    }
}

export function default_queries(
    query: string,
    options: QueryConfig,
) {
    let structured_query = {all: {}}
    if (query) {
        structured_query = {match: {value: query}}
        if (options.query_parser_config) {
            structured_query.match.query_parser_config = options.query_parser_config
        }
    }
    if ((options.language || options.type || options.timerange)) {
        let subqueries = [];
        if (query) {
            subqueries = [{
                query: structured_query,
                occur: 1
            }]
        }
        if (options.language) {
            subqueries.push({
                query: {term: {field: 'languages', value: options.language}},
                occur: 1
            })
        }
        if (options.type === "Books") {
            subqueries.push({
                query: {
                    boolean: {
                        subqueries: [
                            {occur: 0, query: {term: {field: "type", value: "book"}}},
                            {occur: 0, query: {term: {field: "type", value: "edited-book"}}},
                            {occur: 0, query: {term: {field: "type", value: "monograph"}}},
                            {occur: 0, query: {term: {field: "type", value: "reference-book"}}},
                        ]
                    }
                },
                occur: 1,
            })
        }
        if (options.timerange) {
            subqueries.push({
                query: {
                    range: {
                        field: 'issued_at', value: {
                            left: options.timerange[0].toString(), including_left: true,
                            right: options.timerange[1].toString(), including_right: false,
                        }
                    }
                },
                occur: 1
            })
        }
        structured_query = {
            boolean: {
                subqueries: subqueries
            }
        }
    }
    return structured_query
}
const TEMPORAL_RANKING_FORMULA = "original_score * custom_score * fastsigm(abs(now - issued_at) / (86400 * 3) + 5, -1)"
const PR_TEMPORAL_RANKING_FORMULA = `${TEMPORAL_RANKING_FORMULA} * 1.96 * fastsigm(iqpr(quantized_page_rank), 0.15)`

export function default_collectors(
    query_config: QueryConfig,
) {
    const page_size = query_config.page_size ?? 5
    if (query_config.random) {
        return [{reservoir_sampling: {limit: query_config.page_size}}, {count: {}}]
    }
    return [{
        top_docs: {
            offset: (query_config.page - 1) * page_size,
            limit: page_size,
            snippet_configs: {abstract: 400, title: 180},
            fields: (query_config.fields != null) || [],
            scorer: query_config.is_date_sorting_enabled
                ? {order_by: 'issued_at'}
                : null
        }
    }, {
        count: {}
    }]
}
