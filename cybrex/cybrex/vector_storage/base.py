from typing import (
    List,
    Optional,
)


class BaseVectorStorage:
    def query(self, query_embedding: List[float], n_chunks: int, where: Optional[dict] = None):
        raise NotImplementedError()
