from typing import Dict, List, Optional

languages = {
    '🇪🇹': 'am',
    '🇦🇪': 'ar',
    '🇩🇪': 'de',
    '🇬🇧': 'en',
    '🏴󠁧󠁢󠁥󠁮󠁧󠁿': 'en',
    '🇪🇸': 'es',
    '🇮🇷': 'fa',
    '🇮🇳': 'hi',
    '🇮🇩': 'id',
    '🇮🇹': 'it',
    '🇯🇵': 'ja',
    '🇲🇾': 'ms',
    '🇧🇷': 'pb',
    '🇷🇺': 'ru',
    '🇹🇯': 'tg',
    '🇺🇦': 'uk',
    '🇺🇿': 'uz',
}


def _nexus_science_default_scorer_functions(query):
    if 'order_by:date' in query:
        return {'eval_expr': 'issued_at'}
    else:
        return {'eval_expr': "original_score * fastsigm(abs(now - issued_at) / (86400 * 3) + 5, -1) * "
                             "1.96 * fastsigm(iqpr(quantized_page_rank), 0.15)"}


def _nexus_books_default_scorer_functions(query):
    if 'order_by:date' in query:
        return {
            'eval_expr': 'issued_at'
        }
    else:
        return {
            'eval_expr': "original_score * fastsigm(abs(now - issued_at) / (86400 * 3) + 5, -1)"
        }


default_scorer_functions = {
    'nexus_books': _nexus_books_default_scorer_functions,
    'nexus_science': _nexus_science_default_scorer_functions,
}


class QueryProcessor:
    def __init__(self, profile: str):
        self.query_builders = {}
        for index_alias in ['nexus_books', 'nexus_science']:
            self.query_builders[index_alias] = IndexQueryBuilder.from_profile(
                index_alias,
                profile
            )

    def process_overriden_indices(self, query):
        overriden_index_aliases = []

        if '📚' in query:
            query = query.replace('📚', '')
            overriden_index_aliases.append('nexus_books')

        if '🔬' in query:
            query = query.replace('🔬', '')
            overriden_index_aliases.append('nexus_science')

        return query, overriden_index_aliases

    def process_language(self, query):
        for term in query.split():
            if term in languages:
                query.replace(term, f'language:+{languages[term]}')

        return query

    def process_upstream_requesting(self, query):
        is_upstream = False
        omit_telegram_cache = False

        if '⚡⚡⚡' in query:
            query = query.replace('⚡⚡⚡', '').strip()
            is_upstream = True
        if '⚡️⚡️⚡️' in query:
            query = query.replace('⚡️⚡️⚡️', '').strip()
            is_upstream = True
        if '⚡️️⚡️️⚡️️' in query:
            query = query.replace('⚡️️⚡️️⚡️️', '').strip()
            is_upstream = True
        if '⚡️️️️️️️⚡️️️️️️️⚡️️️️️️️' in query:
            query = query.replace('⚡️️️️️️️⚡️️️️️️️⚡️️️️️️️', '').strip()
            is_upstream = True
        if '⚡' in query or '⚡️' in query or '⚡️' in query:
            query = query.replace('⚡', '').strip()
            omit_telegram_cache = True

        return query, is_upstream, omit_telegram_cache

    def process(
        self,
        query: str,
        page_size: int,
        page: int = 0,
        is_fieldnorms_scoring_enabled: Optional[bool] = None,
        index_aliases: Optional[List[str]] = None,
        collector: str = 'top_docs',
        extra_filter: Optional[Dict] = None,
        fields: Optional[List[str]] = None,
    ):
        queries = []
        query, overriden_index_aliases = self.process_overriden_indices(query)
        index_aliases = overriden_index_aliases or index_aliases
        query = self.process_language(query)

        for index_alias in index_aliases:
            queries.append(self.query_builders[index_alias].build(
                query,
                page,
                page_size,
                is_fieldnorms_scoring_enabled=is_fieldnorms_scoring_enabled,
                collector=collector,
                extra_filter=extra_filter,
                fields=fields,
            ))
        return queries


class IndexQueryBuilder:

    def __init__(
        self,
        index_alias: str,
        scorer_function,
        snippet_configs: Optional[Dict] = None,
        is_fieldnorms_scoring_enabled: bool = False,
        exact_matches_promoter: Optional[Dict] = None,
        page: int = 0,
        page_size: int = 5,
    ):
        self.index_alias = index_alias
        self.scorer_function = scorer_function
        self.snippet_configs = snippet_configs
        self.is_fieldnorms_scoring_enabled = is_fieldnorms_scoring_enabled
        self.exact_matches_promoter = exact_matches_promoter
        self.page = page
        self.page_size = page_size

    @staticmethod
    def from_profile(index_alias: str, profile: str):
        match profile:
            case 'light':
                return IndexQueryBuilder(
                    index_alias=index_alias,
                    scorer_function=lambda query: None,
                    snippet_configs={
                        'title': 1024,
                        'abstract': 100,
                    },
                    is_fieldnorms_scoring_enabled=False,
                    exact_matches_promoter=None,
                )
            case 'full':
                return IndexQueryBuilder(
                    index_alias=index_alias,
                    scorer_function=default_scorer_functions[index_alias],
                    snippet_configs={
                        'title': 1024,
                        'abstract': 100,
                    },
                    is_fieldnorms_scoring_enabled=True,
                    exact_matches_promoter={
                        'slop': 1,
                        'boost': 1.5,
                    }
                )
            case _:
                raise ValueError('incorrect profile')

    def build(
        self,
        query: str,
        page: int,
        page_size: int,
        is_fieldnorms_scoring_enabled: Optional[bool] = None,
        collector: str = 'top_docs',
        extra_filter: Optional[Dict] = None,
        fields: Optional[List[str]] = None,
    ):
        if query:
            query_struct = {'match': {'value': query}}
            if self.exact_matches_promoter:
                query_struct['match']['exact_matches_promoter'] = self.exact_matches_promoter
        else:
            query_struct = {'all': {}}
        if extra_filter:
            query_struct = {
                'boolean': {
                    'subqueries': [{
                        'query': query_struct,
                        'occur': 'must'
                    }, {
                        'query': extra_filter,
                        'occur': 'must'
                    }]
                }
            }

        collector_struct = {
            'limit': page_size,
        }
        if offset := page_size * page:
            collector_struct['offset'] = offset
        if fields:
            collector_struct['fields'] = fields
        if self.snippet_configs:
            collector_struct['snippet_configs'] = self.snippet_configs
        if collector == 'top_docs':
            if scorer := self.scorer_function(query):
                collector_struct['scorer'] = scorer

        return {
            'index_alias': self.index_alias,
            'query': query_struct,
            'collectors': [
                {collector: collector_struct},
                {'count': {}}
            ],
            'is_fieldnorms_scoring_enabled': (
                is_fieldnorms_scoring_enabled
                if is_fieldnorms_scoring_enabled is not None
                else self.is_fieldnorms_scoring_enabled
            ),
        }
