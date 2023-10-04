import dataclasses
import uuid
from typing import (
    Iterable,
    List,
    Optional,
    Tuple,
)

import grpc
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    Range,
    VectorParams,
)

from ..document_chunker import Chunk
from ..exceptions import QdrantStorageNotAvailableError
from .base import BaseVectorStorage


@dataclasses.dataclass
class ScoredChunk:
    chunk: Chunk
    score: float


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
            field_schema=PayloadSchemaType.KEYWORD,
        )

    def get_by_field_values(self, field_values: Iterable[Tuple[str, str]], sort: bool = True) -> List[Chunk]:
        if not self._exists_collection(self.collection_name):
            return []
        points, _ = self.db.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                should=[
                    FieldCondition(
                        key=field,
                        match=MatchValue(value=value)
                    ) for (field, value) in field_values
                ],
            ),
            limit=2 ** 31,
        )
        payloads = [Chunk(**point.payload) for point in points]
        if sort:
            return list(sorted(payloads, key=lambda x: (x.document_id, x.chunk_id)))
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

    def query(self, query_embedding, n_chunks: int, field_values: Optional[Iterable[Tuple[str, str]]] = None) -> List[ScoredChunk]:
        self._ensure_collection(
            collection_name=self.collection_name,
            size=len(query_embedding),
        )
        if n_chunks == 0:
            return []
        query_filter = None
        if field_values:
            conditions = []
            for (field, value) in field_values:
                if isinstance(value, str):
                    conditions.append(FieldCondition(key=field, match=MatchValue(value=value)))
                else:
                    conditions.append(FieldCondition(
                        key=field,
                        range=Range(
                            gte=value,
                            lte=value,
                        )
                    ))
            query_filter = Filter(should=conditions)
        points = self.db.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=n_chunks,
        )
        return [ScoredChunk(chunk=Chunk(**point.payload), score=point.score) for point in points]

    def upsert(self, chunks: List[Chunk]):
        if not chunks:
            return
        embeddings = []
        if chunks[0].embedding:
            embedding_size = len(chunks[0].embedding)
            for chunk in chunks:
                embeddings.append(chunk.embedding)
                chunk.embedding = None
        else:
            embeddings = self.embedding_function([
                chunk.real_text or chunk.text
                for chunk in chunks
            ])
            embedding_size = len(embeddings[0])
            for chunk in chunks:
                chunk.real_text = None
        self._ensure_collection(
            collection_name=self.collection_name,
            size=embedding_size,
        )
        return self.db.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=str(uuid.uuid1()),
                    vector=embedding,
                    payload=dataclasses.asdict(chunk)
                )
                for chunk, embedding in zip(chunks, embeddings)
            ]
        )
