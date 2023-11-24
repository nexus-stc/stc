from typing import (
    List,
    Optional,
)

import orjson
from stc_geck.advices import BaseDocumentHolder
from stc_geck.client import StcGeck

from .base import (
    BaseDataSource,
    SourceDocument,
)


class GeckDataSource(BaseDataSource):
    def __init__(self, geck: StcGeck):
        self.geck = geck

    def _query_function(
        self,
        query: str = '',
        with_language_filter: bool = True,
        with_type_filter: bool = True,
        with_existence_filter: bool = False,
    ):
        subqueries = []
        if with_type_filter:
            subqueries.append({'occur': 'must', 'query': {'boolean': {'subqueries': [
                {'occur': 'should', 'query': {'term': {'field': 'type', 'value': 'book'}}},
                {'occur': 'should', 'query': {'term': {'field': 'type', 'value': 'edited-book'}}},
                {'occur': 'should', 'query': {'term': {'field': 'type', 'value': 'monograph'}}},
                {'occur': 'should', 'query': {'term': {'field': 'type', 'value': 'reference-book'}}},
                {'occur': 'should', 'query': {'term': {'field': 'type', 'value': 'journal-article'}}},
                {'occur': 'should', 'query': {'term': {'field': 'type', 'value': 'wiki'}}},
            ]}}})
        if with_language_filter:
            subqueries.append({'occur': 'must', 'query': {'term': {'field': 'languages', 'value': 'en'}}})
        if with_existence_filter:
            subqueries.append({'occur': 'must', 'query': {'exists': {'field': 'content'}}})
        if query:
            subqueries.append({'occur': 'must', 'query': {'match': {'value': query.lower()}}})
        if subqueries:
            return {'boolean': {'subqueries': subqueries}}
        else:
            return {'all': {}}

    async def stream_documents(
        self,
        query: str,
        limit: int = 0,
    ) -> List[SourceDocument]:
        documents = self.geck.get_summa_client().documents(
            self.geck.index_alias,
            query_filter=self._query_function(query, with_existence_filter=True),
        )
        counter = 0
        async for document in documents:
            document = orjson.loads(document)
            document_holder = BaseDocumentHolder(document)
            document_id = document_holder.get_internal_id()
            if not document_id:
                continue
            yield SourceDocument(
                document=document,
                document_id=document_id,
            )
            counter += 1
            if limit and counter >= limit:
                return

    async def search_documents(
        self,
        query: str,
        limit: int = 5,
        sources: Optional[List[str]] = None
    ) -> List[SourceDocument]:
        documents = await self.geck.get_summa_client().search_documents({
            'index_alias': self.geck.index_alias,
            'query': self._query_function(query),
            'collectors': [{'top_docs': {'limit': limit}}],
            'is_fieldnorms_scoring_enabled': False,
        })
        source_documents = []
        for document in documents:
            document_holder = BaseDocumentHolder(document)
            document_id = document_holder.get_internal_id()
            if not document_id:
                continue
            source_documents.append(SourceDocument(
                document=document,
                document_id=document_id,
            ))
        return source_documents
