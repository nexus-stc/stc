import dataclasses
from typing import Dict, List, Optional

from izihawa_nlptools.language_detect import detect_language
from multidict import MultiDict

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
    '🇹🇷': 'tr',
    '🇺🇦': 'uk',
    '🇺🇿': 'uz',
}


def build_inverse_dict(d: dict):
    inverse = MultiDict()
    r = dict()
    for k, v in d.items():
        inverse.add(v, k)
    for k in inverse:
        allvalues = inverse.getall(k)
        if len(allvalues) > 1:
            r[k] = '(' + ' '.join(inverse.getall(k)) + ')'
        else:
            r[k] = allvalues[0]
    return r


default_icon = '📝'
type_icons = {
    'book': '📚',
    'book-chapter': '🔖',
    'chapter': '🔖',
    'dataset': '📊',
    'component': '📊',
    'dissertation': '🧑‍🎓',
    'edited-book': '📚',
    'journal-article': '🔬',
    'monograph': '📚',
    'peer-review': '🤝',
    'proceedings': '📚',
    'proceedings-article': '🔬',
    'reference-book': '📚',
    'report': '📝',
    'standard': '🛠',
}


def get_type_icon(type_):
    return type_icons.get(type_, default_icon)


inversed_type_icons = build_inverse_dict(type_icons)


def _nexus_science_default_scorer_functions(query):
    if query and 'order_by:date' in query:
        return {'eval_expr': 'issued_at'}
    else:
        return {'eval_expr': "original_score * custom_score * fastsigm(abs(now - issued_at) / (86400 * 30) + 5, -1) * "
                             "1.96 * fastsigm(iqpr(quantized_page_rank), 0.15)"}


def _nexus_free_default_scorer_functions(query):
    if query and 'order_by:date' in query:
        return {
            'eval_expr': 'issued_at'
        }
    else:
        return {
            'eval_expr': "original_score * custom_score * fastsigm(abs(now - issued_at) / (86400 * 30) + 5, -1)"
        }


default_field_aliases = {
    'nexus_free': {
        'author': 'authors.name',
        'authors': 'authors.name',
        'cid': 'links.cid',
        'isbns': 'id.isbns',
        'issns': 'metadata.issns',
        'lang': 'language',
        'pub': 'metadata.publisher',
        'ser': 'metadata.series',
    },
    'nexus_science': {
        'author': 'authors.family',
        'authors': 'authors.family',
        'cid': 'links.cid',
        'ev': 'metadata.event.name',
        'isbns': 'metadata.isbns',
        'issns': 'metadata.issns',
        'lang': 'language',
        'pub': 'metadata.publisher',
        'rd': 'references.doi',
        'ser': 'metadata.series',
    }
}

default_scorer_functions = {
    'nexus_free': _nexus_free_default_scorer_functions,
    'nexus_science': _nexus_science_default_scorer_functions,
}

default_removed_fields = {
    'nexus_free': ["doi", "rd", "ev"],
    'nexus_science': ["id"],
}

default_term_field_mapper_configs = {
    'nexus_free': {
        'doi_isbn': {'fields': ['id.isbns']},
        'isbn': {'fields': ['id.isbns']},
    },
    'nexus_science': {
        'doi': {'fields': ['doi']},
        'doi_isbn': {'fields': ['metadata.isbns']},
        'isbn': {'fields': ['metadata.isbns']},
    }
}


@dataclasses.dataclass
class PreprocessedQuery:
    query: str
    is_upstream: bool = False
    skip_ipfs: bool = False
    skip_doi_isbn_term_field_mapper: bool = False
    skip_telegram_cache: bool = False


class QueryProcessor:
    def __init__(self, profile: str):
        self.query_builders = {}
        for index_alias in ['nexus_free', 'nexus_science']:
            self.query_builders[index_alias] = IndexQueryBuilder.from_profile(
                index_alias,
                profile
            )

    def process_filters(self, query):
        for term in query.split():
            if term in inversed_type_icons:
                query = query.replace(term, f' type:+{inversed_type_icons[term]} ')
            if term in languages:
                query = query.replace(term, f' language:+{languages[term]} ')
        return query

    def preprocess_query(self, query):
        preprocessed_query = PreprocessedQuery(query=query)

        if '!:333' in query:
            preprocessed_query.query = preprocessed_query.query.replace('!:333', '').strip()
            preprocessed_query.is_upstream = True
            preprocessed_query.skip_ipfs = True
            preprocessed_query.skip_telegram_cache = True
        if '!:33' in query:
            preprocessed_query.query = preprocessed_query.query.replace('!:33', '').strip()
            preprocessed_query.skip_ipfs = True
            preprocessed_query.skip_telegram_cache = True
        if '!:3' in query:
            preprocessed_query.query = preprocessed_query.query.replace('!:33', '').strip()
            preprocessed_query.skip_telegram_cache = True

        if '#r' in query:
            preprocessed_query.query = preprocessed_query.query.replace('#r', '').strip()
            preprocessed_query.skip_doi_isbn_term_field_mapper = True

        return preprocessed_query

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
            skip_doi_isbn_term_field_mapper: bool = False,
    ):
        queries = []
        query = self.process_filters(query)

        for index_alias in index_aliases:
            queries.append(self.query_builders[index_alias].build(
                query,
                page,
                page_size,
                is_fieldnorms_scoring_enabled=is_fieldnorms_scoring_enabled,
                collector=collector,
                extra_filter=extra_filter,
                fields=fields,
                skip_doi_isbn_term_field_mapper=skip_doi_isbn_term_field_mapper,
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
            removed_fields: Optional[List] = None,
            term_field_mapper_configs: Optional[Dict] = None,
            page: int = 0,
            page_size: int = 5,
    ):
        self.index_alias = index_alias
        self.scorer_function = scorer_function
        self.snippet_configs = snippet_configs
        self.is_fieldnorms_scoring_enabled = is_fieldnorms_scoring_enabled
        self.exact_matches_promoter = exact_matches_promoter
        self.term_field_mapper_configs = term_field_mapper_configs
        self.removed_fields = removed_fields
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
                        'abstract': 140,
                    },
                    is_fieldnorms_scoring_enabled=False,
                    exact_matches_promoter=None,
                    term_field_mapper_configs={
                        'doi': {'fields': ['doi']},
                        'doi_isbn': {'fields': ['metadata.isbns']},
                        'isbn': {'fields': ['metadata.isbns']},
                    }
                )
            case 'full':
                return IndexQueryBuilder(
                    index_alias=index_alias,
                    scorer_function=default_scorer_functions[index_alias],
                    snippet_configs={
                        'title': 1024,
                        'abstract': 140,
                    },
                    is_fieldnorms_scoring_enabled=True,
                    exact_matches_promoter={
                        'slop': 0,
                        'boost': 1.5,
                        'fields': ['abstract', 'extra', 'title']
                    },
                    removed_fields=default_removed_fields[index_alias],
                    term_field_mapper_configs=default_term_field_mapper_configs[index_alias]
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
            skip_doi_isbn_term_field_mapper: bool = False,
    ):
        query = query.lower()
        if query:
            query_value = query.replace('order_by:date', '').strip()
            query_struct = {'match': {'value': query_value}}
            query_language = detect_language(query_value)
            query_parser_config = {
                'query_language': query_language or 'en',
                'term_limit': 20,
                'field_aliases': default_field_aliases[self.index_alias],
            }
            if self.exact_matches_promoter:
                query_parser_config['exact_matches_promoter'] = self.exact_matches_promoter
            if self.term_field_mapper_configs:
                term_field_mapper_configs = self.term_field_mapper_configs
                if skip_doi_isbn_term_field_mapper and 'doi_isbn' in self.term_field_mapper_configs:
                    term_field_mapper_configs = dict(term_field_mapper_configs)
                    term_field_mapper_configs.pop('doi_isbn', None)
                query_parser_config['term_field_mapper_configs'] = term_field_mapper_configs
            query_struct['match']['query_parser_config'] = query_parser_config
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
        if collector == 'top_docs':
            if scorer := self.scorer_function(query):
                collector_struct['scorer'] = scorer
            if self.snippet_configs:
                collector_struct['snippet_configs'] = self.snippet_configs
            if offset := page_size * page:
                collector_struct['offset'] = offset
        if fields:
            collector_struct['fields'] = fields
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
