from typing import (
    List,
    Optional,
)

import orjson
from stc_geck.client import StcGeck

from .base import (
    BaseDataSource,
    SourceDocument,
)


class GeckDataSource(BaseDataSource):
    def __init__(self, geck: StcGeck):
        self.geck = geck

    async def query_documents(
        self,
        query: str,
        limit: int = 5,
        sources: Optional[List[str]] = None
    ) -> List[SourceDocument]:
        queries = self.geck.get_query_processor().process(query, limit=limit, index_aliases=sources)
        response = await self.geck.get_summa_client().search(queries)
        source_documents = []
        for scored_document in response.collector_outputs[0].documents.scored_documents:
            document = orjson.loads(scored_document.document)
            match scored_document.index_alias:
                case 'nexus_science':
                    document_id = f'nexus_science:doi:{document["doi"]}'
                case 'nexus_free':
                    if 'id' in document:
                        if 'isbns' in document['id']:
                            document_id = f'nexus_free:id.isbns:{document["id"]["isbns"][0]}'
                        elif 'internal_iso' in document['id']:
                            document_id = f'nexus_free:id.internal_iso:{document["id"]["internal_iso"]}'
                        else:
                            continue
                    else:
                        continue
                case _:
                    raise RuntimeError("Unsupported table")
            source_documents.append(SourceDocument(
                document=document,
                document_id=document_id,
            ))
        return source_documents
