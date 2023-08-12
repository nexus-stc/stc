import dataclasses
import logging
from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from .advices import (
    PR_TEMPORAL_RANKING_FORMULA,
    TEMPORAL_RANKING_FORMULA,
)
from .utils import (
    inversed_type_icons,
    languages,
)


def _nexus_science_default_scorer_functions(query):
    if query and 'order_by:date' in query:
        return {'eval_expr': 'issued_at'}
    else:
        return {'eval_expr': PR_TEMPORAL_RANKING_FORMULA}


def _nexus_free_default_scorer_functions(query):
    if query and 'order_by:date' in query:
        return {
            'eval_expr': 'issued_at'
        }
    else:
        return {
            'eval_expr': TEMPORAL_RANKING_FORMULA
        }


default_field_aliases = {
    'nexus_free': {
        'author': 'authors.name',
        'authors': 'authors.name',
        'cid': 'links.cid',
        'extension': 'links.extension',
        'format': 'links.extension',
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
        'extension': 'links.extension',
        'format': 'links.extension',
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
    'nexus_free': ["doi", "rd", "ev", "concepts"],
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
        limit: int,
        offset: int = 0,
        is_fieldnorms_scoring_enabled: Optional[bool] = None,
        index_aliases: Optional[List[str]] = None,
        collector: str = 'top_docs',
        extra_filter: Optional[Dict] = None,
        fields: Optional[Union[List[str], Dict[str, List[str]]]] = None,
        skip_doi_isbn_term_field_mapper: bool = False,
        query_language: str = 'en',
    ):
        queries = []
        query = self.process_filters(query)
        if not index_aliases:
            index_aliases = ["nexus_free", "nexus_science"]
        if isinstance(fields, List):
            new_fields = {}
            for index_alias in index_aliases:
                new_fields[index_alias] = fields
            fields = new_fields
        for index_alias in index_aliases:
            queries.append(self.query_builders[index_alias].build(
                query,
                limit,
                offset,
                is_fieldnorms_scoring_enabled=is_fieldnorms_scoring_enabled,
                collector=collector,
                extra_filter=extra_filter,
                fields=fields[index_alias] if fields else None,
                skip_doi_isbn_term_field_mapper=skip_doi_isbn_term_field_mapper,
                query_language=query_language,
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
    ):
        self.index_alias = index_alias
        self.scorer_function = scorer_function
        self.snippet_configs = snippet_configs
        self.is_fieldnorms_scoring_enabled = is_fieldnorms_scoring_enabled
        self.exact_matches_promoter = exact_matches_promoter
        self.term_field_mapper_configs = term_field_mapper_configs
        self.removed_fields = removed_fields

    @staticmethod
    def from_profile(index_alias: str, profile: str):
        logging.getLogger('statbox').info({
            'action': 'build_query_processor',
            'index_alias': index_alias,
            'profile': profile,
        })
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
                    term_field_mapper_configs=default_term_field_mapper_configs[index_alias]
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
        limit: int,
        offset: int,
        is_fieldnorms_scoring_enabled: Optional[bool] = None,
        collector: str = 'top_docs',
        extra_filter: Optional[Dict] = None,
        fields: Optional[List[str]] = None,
        skip_doi_isbn_term_field_mapper: bool = False,
        query_language: str = 'en'
    ):
        query = query.lower()
        if query:
            query_value = query.replace('order_by:date', '').strip()
            query_struct = {'match': {'value': query_value}}
            query_parser_config = {
                'query_language': query_language,
                'term_limit': 20,
                'field_aliases': default_field_aliases[self.index_alias],
                'field_boosts': {
                    'title': 1.3,
                    'extra': 0.3,
                }
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
            'limit': limit,
        }
        if collector == 'top_docs':
            if scorer := self.scorer_function(query):
                collector_struct['scorer'] = scorer
            if self.snippet_configs:
                collector_struct['snippet_configs'] = self.snippet_configs
            if offset:
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
