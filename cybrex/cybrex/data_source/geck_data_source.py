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
        query = self.geck.get_query_processor().process(query, limit=limit)
        response = await self.geck.get_summa_client().search(query)
        source_documents = []
        for scored_document in response.collector_outputs[0].documents.scored_documents:
            document = orjson.loads(scored_document.document)
            if 'dois' in document['id']:
                document_id = f'id.dois:{document["id"]["dois"][0]}'
            elif 'nexus_id' in document['id']:
                document_id = f'id.nexus_id:{document["id"]["nexus_id"]}'
            elif 'internal_iso' in document['id']:
                document_id = f'id.internal_iso:{document["id"]["internal_iso"]}'
            elif 'internal_bs' in document['id']:
                document_id = f'id.internal_bs:{document["id"]["internal_bs"]}'
            elif 'arc_ids' in document['id']:
                document_id = f'id.arc_ids:{document["id"]["arc_ids"][0]}'
            elif 'libgen_ids' in document['id']:
                document_id = f'id.libgen_ids:{document["id"]["libgen_ids"][0]}'
            elif 'zlibrary_ids' in document['id']:
                document_id = f'id.zlibrary_ids:{document["id"]["zlibrary_ids"][0]}'
            else:
                continue
            source_documents.append(SourceDocument(
                document=document,
                document_id=document_id,
            ))
        return source_documents
