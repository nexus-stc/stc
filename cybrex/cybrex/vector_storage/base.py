from typing import (
    Iterable,
    List,
    Optional,
    Tuple,
)


class BaseVectorStorage:
    def query(self, query_embedding: List[float], n_chunks: int, field_values: Optional[Iterable[Tuple[str, str]]] = None):
        raise NotImplementedError()
