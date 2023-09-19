import uuid
from typing import List

import grpc
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)

from ..exceptions import QdrantStorageNotAvailableError
from .base import BaseVectorStorage


class QdrantVectorStorage(BaseVectorStorage):
    def __init__(self, qdrant_config, collection_name, embedding_function, force_recreate: bool = False):
        self.db = QdrantClient(**qdrant_config)
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        self.force_recreate = force_recreate
        self.is_existing = False

    def _exists_collection(self, collection_name):
        if self.is_existing:
            return True
        try:
            collections = self.db.get_collections()
        except grpc.RpcError:
            raise QdrantStorageNotAvailableError()
        for collection in collections.collections:
            if collection.name == collection_name:
                self.is_existing = True
                return True
        return False

    def _ensure_collection(self, collection_name, size):
        if not self.force_recreate:
            if self._exists_collection(collection_name):
                return
            self.db.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE),
            )
        else:
            self.db.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE),
            )
            self.force_recreate = False
        self.is_existing = True
        self.db.create_payload_index(
            collection_name=collection_name,
            field_name="document_id",
            field_schema="keyword",
        )

    def get_by_field_value(self, field, value, sort: bool = True) -> List[dict]:
        if not self._exists_collection(self.collection_name):
            return []
        points, _ = self.db.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                should=[
                    FieldCondition(
                        key=field,
                        match=MatchValue(value=value)
                    ),
                ],
            ),
            limit=2 ** 31,
        )
        payloads = [point.payload for point in points]
        if sort:
            return list(sorted(payloads, key=lambda x: x['chunk_id']))
        return payloads

    def exists_by_field_value(self, field, value) -> bool:
        if not self._exists_collection(self.collection_name):
            return False
        points, _ = self.db.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                should=[
                    FieldCondition(
                        key=field,
                        match=MatchValue(value=value)
                    ),
                ],
            ),
            with_payload=False,
            limit=1,
        )
        return len(points) > 0

    def query(self, query_embedding, n_chunks: int, where: dict = None):
        self._ensure_collection(
            collection_name=self.collection_name,
            size=len(query_embedding),
        )
        if n_chunks == 0:
            return []
        query_filter = None
        if where:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key=k,  # Condition based on values of `rand_number` field.
                        range=Range(
                            gte=v,
                            lte=v
                        )
                    ) for k, v in where.items()
                ]
            )
        points = self.db.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=n_chunks,
        )
        return [{**point.payload, 'score': point.score} for point in points]

    def upsert(self, chunks: List[dict]):
        if not chunks:
            return
        if 'embedding' in chunks[0]:
            embeddings = [chunk.pop('embedding') for chunk in chunks]
        else:
            embeddings = self.embedding_function([
                chunk.pop('real_text', None) or chunk['text']
                for chunk in chunks
            ])
        self._ensure_collection(
            collection_name=self.collection_name,
            size=len(embeddings[0]),
        )
        return self.db.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=str(uuid.uuid1()),
                    vector=embedding,
                    payload=chunk
                )
                for chunk, embedding in zip(chunks, embeddings)
            ]
        )
