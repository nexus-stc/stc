import uuid
from typing import List

import chromadb

from .base import BaseVectorStorage


class ChromaVectorStorage(BaseVectorStorage):
    def __init__(self, path, collection_name, embedding_function=None):
        self.db = chromadb.PersistentClient(path=path)
        self.collection_name = collection_name
        self.collection = self.db.get_or_create_collection(
            name=self.collection_name,
            embedding_function=embedding_function,
        )

    def _unpack(self, chroma_response, i: int = 0) -> List[dict]:
        chunks = []
        documents = chroma_response.get('documents', [])
        if documents and isinstance(documents[0], list):
            documents = documents[i]

        metadatas = chroma_response.get('metadatas', [])
        if metadatas and isinstance(metadatas[0], list):
            metadatas = metadatas[i]

        distances = chroma_response.get('distances', [])
        if distances and isinstance(distances[0], list):
            distances = distances[i]

        for j in range(len(metadatas)):
            chunk = {}
            if documents:
                chunk['text'] = documents[j]
            if metadatas:
                chunk['metadata'] = metadatas[j]
            if distances:
                chunk['distance'] = distances[j]
            chunks.append(chunk)
        return chunks

    def _pack(self, chunks):
        embeddings = []
        metadatas = []
        texts = []
        for chunk in chunks:
            if 'embedding' in chunk:
                embeddings.append(chunk['embedding'])
            if 'metadata' in chunk:
                metadatas.append(chunk['metadata'])
            if 'text' in chunk:
                texts.append(chunk['text'])
        return embeddings, metadatas, texts

    def get_by_field_value(self, field, value) -> List[dict]:
        chrome_response = self.collection.get(where={field: value})
        return self._unpack(chrome_response)

    def query(self, query_embeddings, n_chunks: int, where: dict = None):
        responses = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=n_chunks,
            include=['documents', 'metadatas', 'distances'],
            where=where,
        )
        unpacked_responses = []
        for i in range(len(responses["documents"])):
            unpacked_responses.append(self._unpack(responses, i=i))
        return unpacked_responses

    def upsert(self, chunks: List[dict]):
        embeddings, metadatas, texts = self._pack(chunks)
        return self.collection.upsert(
            embeddings=embeddings or None,
            documents=texts or None,
            metadatas=metadatas or None,
            ids=[str(uuid.uuid1()) for _ in range(len(embeddings or texts))]
        )
