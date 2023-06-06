from aiokit import AioThing

from tgbot.app.exceptions import InvalidSearchError, UnavailableSummaError


class SummaWrapper(AioThing):
    def __init__(self, config):
        super().__init__()
        self.is_read_only = False

        if 'aiosumma' in config:
            from aiosumma import SummaClient
            from grpc import StatusCode
            from grpc.aio import AioRpcError
            self.summa_client = SummaClient(
                endpoint=config['aiosumma']['endpoint'],
                max_message_length=2 * 1024 * 1024 * 1024 - 1,
            )

            async def wrapped_search(queries):
                try:
                    return await self.summa_client.search(queries)
                except AioRpcError as e:
                    if e.code() == StatusCode.INVALID_ARGUMENT:
                        raise InvalidSearchError(search=queries)
                    elif e.code() == StatusCode.CANCELLED:
                        raise UnavailableSummaError()
                    raise e

            self.search = wrapped_search
        elif 'ipfs' in config:
            from stc_geck.client import StcGeck
            paths = config['ipfs']['paths']
            self.summa_client = StcGeck(
                ipfs_http_endpoint=config['ipfs']['base_url'],
                paths=paths.split(',') if isinstance(paths, str) else paths,
            )

            async def wrapped_search(queries):
                return await self.summa_client.search(queries)

            self.search = wrapped_search
            self.is_read_only = True
        else:
            raise RuntimeError("Unknown Summa config")
        self.starts.append(self.summa_client)

    def commit_index(self, index_alias):
        return self.summa_client.commit_index(index_alias)

    def index_document(self, index_alias, document):
        return self.summa_client.index_document(index_alias, document)

    def get_one_by_field_value(self, index_alias, field, value):
        return self.summa_client.get_one_by_field_value(index_alias, field, value)