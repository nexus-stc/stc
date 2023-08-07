from typing import (
    List,
    Optional,
)


class BaseVectorStorage:
    async def query(self, query_embeddings: List[List[float]], n_chunks: int, where: Optional[dict] = None):
        raise NotImplementedError()
