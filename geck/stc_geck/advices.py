from typing import (
    List,
    Optional,
)

from aiosumma import SummaClient

TEMPORAL_RANKING_FORMULA = "original_score * custom_score * fastsigm(abs(now - issued_at) / (86400 * 3) + 5, -1)"
PR_TEMPORAL_RANKING_FORMULA = f"{TEMPORAL_RANKING_FORMULA} * 1.96 * fastsigm(iqpr(quantized_page_rank), 0.15)"


default_field_aliases = {
    'author': 'authors.family',
    'authors': 'authors.family',
    'cid': 'links.cid',
    'doi': 'id.dois',
    'ev': 'metadata.event.name',
    'extension': 'links.extension',
    'format': 'links.extension',
    'isbn': 'metadata.isbns',
    'isbns': 'metadata.isbns',
    'issn': 'metadata.issns',
    'issns': 'metadata.issns',
    'lang': 'languages',
    'pub': 'metadata.publisher',
    'rd': 'references.doi',
    'ser': 'metadata.series',
}


default_term_field_mapper_configs = {
    'doi': {'fields': ['id.dois']},
    'doi_isbn': {'fields': ['metadata.isbns']},
    'isbn': {'fields': ['metadata.isbns']},
}


default_field_boosts = {
    'authors': 2.0,
    'extra': 0.3,
    'title': 2.0,
}


async def get_documents_on_topic(
    summa_client: SummaClient,
    topic: str,
    documents: int = 20,
    index_alias: str = 'nexus_science',
    ranking_formula: Optional[str] = None,
    is_fieldnorms_scoring_enabled: bool = False,
    default_fields: List[str] = ("abstract", "title", "content"),
):
    return await summa_client.search_documents({
        "index_alias": index_alias,
        "query": {"boolean": {"subqueries": [{
            "occur": "should",
            "query": {
                "match": {
                    "value": topic,
                    "query_parser_config": {
                        "default_fields": list(default_fields),
                        "field_aliases": default_field_aliases,
                        "field_boosts": default_field_boosts,
                    },
                }
            },
        }]}},
        "collectors": [{"top_docs": {"limit": documents, "scorer": {
            "eval_expr": ranking_formula or PR_TEMPORAL_RANKING_FORMULA,
        }}}],
        "is_fieldnorms_scoring_enabled": is_fieldnorms_scoring_enabled,
    })


def get_full_query_parser_config(query_language: Optional[str] = None):
    query_parser_config = {
        'default_fields': ['abstract', 'concepts', 'content', 'extra', 'title'],
        'term_limit': 20,
        'field_aliases': default_field_aliases,
        'field_boosts': default_field_boosts,
        'exact_matches_promoter': {
            'slop': 0,
            'boost': 2.0,
            'fields': ['abstract', 'extra', 'title']
        }
    }
    if query_language:
        query_parser_config['query_language'] = query_language
    return query_parser_config


def get_light_query_parser_config(query_language: Optional[str] = None):
    query_parser_config = {
        'default_fields': ['abstract', 'title'],
        'term_limit': 20,
        'field_aliases': default_field_aliases,
        'field_boosts': default_field_boosts,
    }
    if query_language:
        query_parser_config['query_language'] = query_language
    return query_parser_config


def get_query_parser_config(profile: str, query_language: Optional[str] = None):
    match profile:
        case 'full': return get_full_query_parser_config(query_language)
        case 'light': return get_light_query_parser_config(query_language)
        case _: raise ValueError("Unknown profile")


def get_default_scorer(profile: str):
    match profile:
        case 'full': return {'eval_expr': PR_TEMPORAL_RANKING_FORMULA}
        case 'light': return None
        case _: raise ValueError("Unknown profile")
