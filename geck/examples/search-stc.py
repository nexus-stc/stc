import argparse
import asyncio

from stc_geck.advices import format_document
from stc_geck.client import StcGeck

DEFAULT_LIMIT = 5


async def main(limit: int):
    geck = StcGeck(
        ipfs_http_base_url='http://127.0.0.1:8080',
        timeout=300,
    )

    # Connects to IPFS and instantiate configured indices for searching
    # It will take a time depending on your IPFS performance
    await geck.start()

    # GECK encapsulates Python client to Summa.
    # It can be either external stand-alone server or embed server,
    # but details are hidden behind `SummaClient` interface.
    summa_client = geck.get_summa_client()

    # Match search returns top-5 documents which contain `additive manufacturing` in their title, abstract or content.
    documents = await summa_client.search_documents({
        "index_alias": "nexus_science",
        "query": {
            "match": {
                "value": "additive manufacturing",
                "query_parser_config": {"default_fields": ["abstract", "title", "content"]}
            }
        },
        "collectors": [{"top_docs": {"limit": limit}}],
        "is_fieldnorms_scoring_enabled": False,
    })

    for document in documents:
        print(format_document(document) + '\n')

    await geck.stop()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--limit', type=int, default=DEFAULT_LIMIT)
    args = argparser.parse_args()

    asyncio.run(main(args.limit))
