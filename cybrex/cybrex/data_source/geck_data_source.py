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
        queries = self.geck.get_query_processor().process(query, limit=limit)
        response = await self.geck.get_summa_client().search(queries)
        source_documents = []
        for scored_document in response.collector_outputs[0].documents.scored_documents:
            document = orjson.loads(scored_document.document)
            if 'dois' in document['id']:
                document_id = f'doi:{document["dois"][0]}'
            elif 'libgen_ids' in document['libgen_ids']:
                document_id = f'libgen_ids:{document["dois"][0]}'
            source_documents.append(SourceDocument(
                document=document,
                document_id=document_id,
            ))
        return source_documents
