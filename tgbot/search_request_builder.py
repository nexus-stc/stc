import dataclasses
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from multidict import MultiDict
from stc_geck.advices import (
    default_term_field_mapper_configs,
    get_default_scorer,
    get_query_parser_config,
)

from library.sciparse.language_detect import detect_language

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
        r[k] = inverse.getall(k)
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
    query_language: Optional[str] = None


class TelegramSearchRequestBuilder:
    def __init__(self, index_alias: str, profile: str):
        self.index_alias = index_alias
        self.profile = profile
        self.default_is_fieldnorms_scoring_enabled = profile == 'full'

    def extract_traits(self, string_query: str) -> Tuple[str, ExtraQueryTraits]:
        extra_query_traits = ExtraQueryTraits(
            languages=[],
            types=[],
        )
        extra_query_traits.query_language = detect_language(string_query)

        for term in string_query.split():
            if term in inversed_type_icons:
                extra_query_traits.types.extend(inversed_type_icons[term])
                string_query = string_query.replace(term, '').strip()
            if term in languages:
                extra_query_traits.languages.append(languages[term])
                string_query = string_query.replace(term, '').strip()

        if '!:333' in string_query:
            string_query = string_query.replace('!:333', '').strip()
            extra_query_traits.is_upstream = True
            extra_query_traits.skip_ipfs = True
            extra_query_traits.skip_telegram_cache = True
        if '!:33' in string_query:
            string_query = string_query.replace('!:33', '').strip()
            extra_query_traits.skip_ipfs = True
            extra_query_traits.skip_telegram_cache = True
        if '!:3' in string_query:
            string_query = string_query.replace('!:33', '').strip()
            extra_query_traits.skip_telegram_cache = True

        if '#r' in string_query:
            string_query = string_query.replace('#r', '').strip()
            extra_query_traits.skip_doi_isbn_term_field_mapper = True

        if 'order_by:date' in string_query:
            string_query = string_query.replace('order_by:date', '').strip()
            extra_query_traits.order_by_date = True

        return string_query, extra_query_traits

    def process(
        self,
        string_query: str,
        limit: int,
        offset: int = 0,
        is_fieldnorms_scoring_enabled: Optional[bool] = None,
        collector: str = 'top_docs',
        extra_filter: Optional[Dict] = None,
        fields: Optional[Union[List[str]]] = None,
        default_query_language: Optional[str] = None
    ):
        string_query, query_traits = self.extract_traits(string_query)

        if string_query:
            query_parser_config = get_query_parser_config(self.profile, query_traits.query_language or default_query_language)
            term_field_mapper_configs = default_term_field_mapper_configs
            if query_traits.skip_doi_isbn_term_field_mapper and 'doi_isbn' in term_field_mapper_configs:
                term_field_mapper_configs = dict(term_field_mapper_configs)
                term_field_mapper_configs.pop('doi_isbn', None)
            query_parser_config['term_field_mapper_configs'] = term_field_mapper_configs
            query = {'match': {'value': string_query.lower(), 'query_parser_config': query_parser_config}}
        else:
            query = {'all': {}}
        all_extra_filters = []
        if extra_filter:
            all_extra_filters.append(extra_filter)
        if query_traits.languages:
            all_extra_filters.append({'boolean': {'subqueries': [
                {'occur': 'should', 'query': {'term': {'field': 'languages', 'value': language}}}
                for language in query_traits.languages
            ]}})
        if query_traits.types:
            all_extra_filters.append({'boolean': {'subqueries': [{'occur': 'should', 'query': {'term': {'field': 'type', 'value': type_}}} for type_ in query_traits.types]}})
        if all_extra_filters:
            subqueries = [{
                'query': query,
                'occur': 'must'
            }]
            subqueries.extend([{'occur': 'must', 'query': q} for q in all_extra_filters])
            query = {'boolean': {
                'subqueries': subqueries
            }}

        collector_struct = {
            'limit': limit,
        }
        if collector == 'top_docs':
            if query_traits.order_by_date:
                collector_struct['scorer'] = {'eval_expr': 'issued_at'}
            elif scorer := get_default_scorer(self.profile):
                collector_struct['scorer'] = scorer
            collector_struct['snippet_configs'] = {
                'title': 1024,
                'abstract': 140,
            }
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
                else self.default_is_fieldnorms_scoring_enabled
            ),
        }, query_traits
