from izihawa_utils.exceptions import BaseError


class IpfsConnectionError(BaseError):
    pass


class ItemNotFound(BaseError):
    def __init__(self, query):
        self.query = query


class CidNotFound(BaseError):
    def __init__(self, query):
        self.query = query
