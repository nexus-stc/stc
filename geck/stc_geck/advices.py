from aiosumma import SummaClient

SHOULD = 0
MUST = 1
MUST_NOT = 2


PR_TEMPORAL_RANKING_FORMULA = "original_score * fastsigm(abs(now - issued_at) / (86400 * 3) + 5, -1) * 1.96 * " \
                              "fastsigm(iqpr(quantized_page_rank), 0.15)"


async def get_documents_on_topic(summa_client: SummaClient, topic: str, documents: int = 20):
    return await summa_client.search_documents([{
        "index_alias": "nexus_science",
        "query": {"query": {"boolean": {"subqueries": [
            {"occur": SHOULD, "query": {
                "query": {"match": {"value": topic, "default_fields": ["title", "abstract"], "field_boosts": {}}}}},
        ]}}},
        "collectors": [{"collector": {"top_docs": {"limit": documents, "scorer": {"scorer": {
            "eval_expr": PR_TEMPORAL_RANKING_FORMULA,
        }}}}}],
        "is_fieldnorms_scoring_enabled": False,
    }])
