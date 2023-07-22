export function default_queries (
  index_alias: string,
  query: string,
  language?: string
) {
  let structured_query = { query: { match: { value: query } } }
  if (language && (index_alias === 'nexus_science' || index_alias === 'nexus_free')) {
    structured_query = {
      query: {
        boolean: {
          subqueries: [{
            query: { query: structured_query.query },
            occur: 1
          }, {
            query: { query: { term: { field: 'language', value: language } } },
            occur: 1
          }]
        }
      }
    }
  }
  return structured_query
}

export function default_collectors (
  index_alias: string,
  options: {
    page: number
    page_size?: number
    fields?: string[]
    is_temporal_scoring_enabled: boolean
    is_date_sorting_enabled: boolean
  }
) {
  const page_size = options.page_size ?? 5
  const defaults = {
    nexus_media: [
      {
        collector: {
          top_docs: {
            offset: (options.page - 1) * page_size,
            limit: page_size,
            snippet_configs: { title: 340 },
            fields: (options.fields != null) || [],
            scorer: options.is_date_sorting_enabled
              ? { scorer: { order_by: 'registered_at' } }
              : options.is_temporal_scoring_enabled
                ? {
                    scorer: {
                      eval_expr: 'original_score * fastsigm(abs(now - registered_at) / (86400 * 3) + 5, -1)'
                    }
                  }
                : null
          }
        }
      },
      { collector: { count: {} } }
    ],
    nexus_free: [
      {
        collector: {
          top_docs: {
            offset: (options.page - 1) * page_size,
            limit: page_size,
            snippet_configs: { abstract: 400, title: 180 },
            scorer: options.is_date_sorting_enabled
              ? { scorer: { order_by: 'issued_at' } }
              : options.is_temporal_scoring_enabled
                ? {
                    scorer: {
                      eval_expr: 'original_score * fastsigm(abs(now - issued_at) / (86400 * 3) + 5, -1)'
                    }
                  }
                : null,
            fields: (options.fields != null) || []
          }
        }
      },
      { collector: { count: {} } }
    ],
    nexus_science: [
      {
        collector: {
          top_docs: {
            offset: (options.page - 1) * page_size,
            limit: page_size,
            snippet_configs: { abstract: 400, title: 180 },
            fields: (options.fields != null) || [],
            scorer: options.is_date_sorting_enabled
              ? { scorer: { order_by: 'issued_at' } }
              : options.is_temporal_scoring_enabled
                ? {
                    scorer: {
                      eval_expr: 'original_score * fastsigm(abs(now - issued_at) / (86400 * 3) + 5, -1) * 1.96 * fastsigm(iqpr(quantized_page_rank), 0.15)'
                    }
                  }
                : null
          }
        }
      },
      { collector: { count: {} } }
    ]
  }
  return defaults[index_alias]
}
