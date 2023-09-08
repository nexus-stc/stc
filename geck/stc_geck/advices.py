from typing import (
    List,
    Optional,
)

from aiosumma import SummaClient

TEMPORAL_RANKING_FORMULA = "original_score * custom_score * fastsigm(abs(now - issued_at) / (86400 * 3) + 5, -1)"
PR_TEMPORAL_RANKING_FORMULA = f"{TEMPORAL_RANKING_FORMULA} * 1.96 * fastsigm(iqpr(quantized_page_rank), 0.15)"


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
                    "query_parser_config": {"default_fields": list(default_fields)}
                }
            },
        }]}},
        "collectors": [{"top_docs": {"limit": documents, "scorer": {
            "eval_expr": ranking_formula or PR_TEMPORAL_RANKING_FORMULA,
        }}}],
        "is_fieldnorms_scoring_enabled": is_fieldnorms_scoring_enabled,
    })
