import json
import asyncio
import argparse
from stc_geck.client import StcGeck

LIMIT = 5

async def get_response(summa_client):


    # Match search returns top-5 documents which contain `additive manufacturing` in their title, abstract or content.
    search_response = await summa_client.search({
        "index_alias": "nexus_science",
        "query": {
            "match": {
                "value": "additive manufacturing",
                "query_parser_config": {"default_fields": ["abstract", "title", "content"]}
            }
        },
        "collectors": [{"top_docs": {"limit": LIMIT}}],
        "is_fieldnorms_scoring_enabled": False,
    })
    return search_response

async def main():
    
    geck = StcGeck(
        ipfs_http_base_url='http://127.0.0.1:8080',
        timeout=300,
    )

    # Connects to IPFS and instantiate configured indices for searching It will take a time depending on your IPFS performance
    await geck.start()

    # GECK encapsulates Python client to Summa. It can be either external stand-alone server or embed server, but details are hidden behind SummaClient interface.
    summa_client = geck.get_summa_client()    
    
    search_response = await get_response(summa_client=summa_client)
    
    for scored_document in search_response.collector_outputs[0].documents.scored_documents:
        
        document = json.loads(scored_document.document)
        
        print('DOI:', document['id']['dois'][0])
        print('Title:', document['title'])
        print('Abstract:', document.get('abstract'))
        print('Links:', document.get('links'))
        print('-----')        
    
    await geck.stop()
    
if __name__ == "__main__":

    argparser = argparse.ArgumentParser()
    argparser.add_argument('--limit', type=int, default=LIMIT)
    args = argparser.parse_args()
    
    LIMIT = args.limit    
    
    asyncio.run(main())
    