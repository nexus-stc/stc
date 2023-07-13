import logging
import re
import tempfile
from typing import Tuple
from urllib.parse import urlparse

import aiohttp
import orjson
import summa_embed
from aiokit import AioThing
from aiosumma import SummaClient

from .utils import create_car


def get_config():
    return {
        'debug': True,
        'api': {
            'http_endpoint': None,
            'max_frame_size_bytes': 2147483648,
            'concurrency_limit': 4,
            'buffer': 8,
        },
        'consumers': {},
        'core': {
            'doc_store_compress_threads': 1,
            'doc_store_cache_num_blocks': 256,
            'indices': {},
            'writer_heap_size_bytes': 1073741824,
        }
    }


def canonoize_base_url(endpoint):
    endpoint = endpoint.rstrip('/')
    if not endpoint.startswith('http'):
        endpoint = 'http://' + endpoint
    return endpoint


async def query_wrapper(response):
    for scored_document in response.collector_outputs[0].documents.scored_documents:
        yield orjson.loads(scored_document.document)


async def load_document(documents):
    async for document in documents:
        document = orjson.loads(document)
        if 'cid' in document:
            yield document


async def detect_host_header(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=False) as resp:
            if 300 <= resp.status < 400:
                redirection_url = resp.headers['Location']
                if 'localhost' in redirection_url:
                    parsed_url = urlparse(redirection_url)
                    return re.search(r'(.*)\.localhost.*', parsed_url.netloc).group(0)


class StcGeck(AioThing):
    def __init__(
        self,
        ipfs_http_base_url: str = 'http://localhost:8080',
        ipfs_data_directory: str = '/ipns/standard-template-construct.org/data',
        index_names: Tuple[str, ...] = ('nexus_science',),
        grpc_api_endpoint: str = '127.0.0.1:10082',
        embed: bool = True,
    ):
        super().__init__()
        self.ipfs_http_base_url = canonoize_base_url(ipfs_http_base_url)
        self.ipfs_data_directory = '/' + ipfs_data_directory.strip('/') + '/'
        self.index_names = index_names
        self.grpc_api_endpoint = grpc_api_endpoint
        self.embed = embed
        self.summa_embed_server = None
        self.summa_client = SummaClient(
            endpoint=self.grpc_api_endpoint,
            max_message_length=2 * 1024 * 1024 * 1024 - 1,
        )
        self.temp_dir = None

    async def start(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        if self.embed:
            server_config = get_config()
            server_config['api']['grpc_endpoint'] = self.grpc_api_endpoint
            server_config['data_path'] = self.temp_dir.name
            server_config['log_path'] = self.temp_dir.name
            for index_name in self.index_names:
                query_parser_config = {
                    'default_fields': ['abstract', 'title']
                }
                full_path = self.ipfs_http_base_url + self.ipfs_data_directory + index_name + '/'
                headers_template = {'range': 'bytes={start}-{end}'}
                remote_index_config = {'remote': {
                    'method': 'GET',
                    'url_template': f'{full_path}{{file_name}}',
                    'headers_template': headers_template,
                    'cache_config': {'cache_size': 536870912},
                }}
                if host_header := await detect_host_header(full_path):
                    headers_template['host'] = host_header
                server_config['core']['indices'][index_name] = {
                    'query_parser_config': query_parser_config,
                    'config': remote_index_config,
                    'field_triggers': {},
                }
            self.summa_embed_server = summa_embed.SummaEmbedServerBin(server_config)
            await self.summa_embed_server.start()
        await self.summa_client.start()

    async def stop(self):
        await self.summa_client.stop()
        if self.summa_embed_server:
            await self.summa_embed_server.stop()
            self.summa_embed_server = None
        self.temp_dir.cleanup()

    def get_summa_client(self):
        return self.summa_client

    async def download(self, cid: str, timeout: int = 120):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(f'{self.ipfs_http_base_url}/ipfs/{cid}') as resp:
                return await resp.read()

    async def create_ipfs_directory(
        self,
        index_name: str,
        output_car: str,
        query: str = None,
        limit: int = 100,
        name_template: str = '{id}.{extension}',
    ):
        if query and self.embed:
            logging.getLogger('warning').warning('Too high limit for embedded Summa')
        if query:
            return await create_car(
                output_car,
                query_wrapper(await self.summa_client.search([{
                    'index_alias': index_name,
                    'collectors': [{'top_docs': {'limit': limit, 'scorer': {'order_by': 'issued_at'}}}],
                    'query': {'boolean': {'subqueries': [
                        {'occur': 'must', 'query': {'match': {'value': query}}},
                        {'occur': 'must', 'query': {'exists': {'field': 'cid'}}},
                    ]}},
                }])),
                limit=limit,
                name_template=name_template,
            )
        else:
            return await create_car(
                output_car,
                load_document(self.summa_client.documents(index_name)),
                limit=limit,
                name_template=name_template,
            )
