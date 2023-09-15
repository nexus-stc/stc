import dataclasses
from typing import Optional, Dict, Union, List, Tuple

from multidict import MultiDict
from stc_geck.query_processor import IndexQueryBuilder

from geck.stc_geck.advices import get_query_parser_config

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


@dataclasses.dataclass
class ExtraQueryTraits:
    types: List[str]
    languages: List[str]
    is_upstream: bool = False
    skip_ipfs: bool = False
    skip_doi_isbn_term_field_mapper: bool = False
    skip_telegram_cache: bool = False
    order_by_date: bool = False


class TelegramQueryPreprocessor:
    def __init__(self, index_alias: str, profile: str):
        self.index_alias = index_alias
        self.profile = profile

    def extract_traits(self, query) -> Tuple[str, ExtraQueryTraits]:
        extra_query_traits = ExtraQueryTraits(
            languages=[],
            types=[],
        )

        for term in query.split():
            if term in inversed_type_icons:
                extra_query_traits.types.append(inversed_type_icons[term])
                query = query.replace(term, '').strip()
            if term in languages:
                extra_query_traits.languages.append(languages[term])
                query = query.replace(term, '').strip()

        if '!:333' in query:
            query = query.replace('!:333', '').strip()
            extra_query_traits.is_upstream = True
            extra_query_traits.skip_ipfs = True
            extra_query_traits.skip_telegram_cache = True
        if '!:33' in query:
            query = query.replace('!:33', '').strip()
            extra_query_traits.skip_ipfs = True
            extra_query_traits.skip_telegram_cache = True
        if '!:3' in query:
            query = query.replace('!:33', '').strip()
            extra_query_traits.skip_telegram_cache = True

        if '#r' in query:
            query = query.replace('#r', '').strip()
            extra_query_traits.skip_doi_isbn_term_field_mapper = True
        if 'order_by:date' in query:
            query = query.replace('order_by:date', '').strip()
            extra_query_traits.order_by_date = True

        return query, extra_query_traits

    def process(
        self,
        string_query: str,
        limit: int,
        offset: int = 0,
        is_fieldnorms_scoring_enabled: Optional[bool] = None,
        collector: str = 'top_docs',
        extra_filter: Optional[Dict] = None,
        fields: Optional[Union[List[str]]] = None,
        skip_doi_isbn_term_field_mapper: bool = False,
        query_language: str = 'en',
    ):
        string_query, query_traits = self.extract_traits(string_query)
        if string_query:
            query = {'match': {'value': string_query.lower()}}
        else:
            query = {'all': {}}
        all_extra_filters = []
        if extra_filter:
            all_extra_filters.append(extra_filter)
        for language in query_traits.languages:
            all_extra_filters.append({'boolean': {'subqueries': [{'occur': 'should', 'query': {'term': {'field': 'languages', 'value': language}}}]}})
        for type_ in query_traits.types:
            all_extra_filters.append({'boolean': {
                'subqueries': [{'occur': 'should', 'query': {'term': {'field': 'type', 'value': type_}}}]}})
        if all_extra_filters:
            subqueries = [{
                'query': query,
                'occur': 'must'
            }]
            subqueries.extend([{'occur': 'must', 'query': q} for q in all_extra_filters])
            query = {'boolean': {
                'subqueries': subqueries
            }}

        query_parser_config = get_query_parser_config(self.profile, query_language)

        if self.term_field_mapper_configs:
            term_field_mapper_configs = self.term_field_mapper_configs
            if skip_doi_isbn_term_field_mapper and 'doi_isbn' in self.term_field_mapper_configs:
                term_field_mapper_configs = dict(term_field_mapper_configs)
                term_field_mapper_configs.pop('doi_isbn', None)
            query_parser_config['term_field_mapper_configs'] = term_field_mapper_configs
        query_struct['match']['query_parser_config'] = query_parser_config
        collector_struct = {
            'limit': limit,
        }
        if collector == 'top_docs':
            if scorer := self.scorer_function:
                collector_struct['scorer'] = scorer
            if snippet_configs:
                collector_struct['snippet_configs'] = self.snippet_configs
            if offset:
                collector_struct['offset'] = offset
        if fields:
            collector_struct['fields'] = fields
        return {
            'index_alias': self.index_alias,
            'query': query,
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


        return self.query_builder.build(
            query,
            limit,
            offset,
            is_fieldnorms_scoring_enabled=is_fieldnorms_scoring_enabled,
            collector=collector,
            fields=fields,
            skip_doi_isbn_term_field_mapper=skip_doi_isbn_term_field_mapper,
            query_language=query_language,
        )