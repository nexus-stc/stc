import re
from typing import List, Tuple
from urllib.parse import urlparse

import aiohttp
import summa_embed


async def detect_host_header(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=False) as resp:
            if 300 <= resp.status < 400:
                redirection_url = resp.headers['Location']
                if 'localhost' in redirection_url:
                    parsed_url = urlparse(redirection_url)
                    return re.search(r'(.*)\.localhost.*', parsed_url.netloc).group(0)


class StcTools:
    def __init__(
        self,
        ipfs_http_endpoint: str = 'http://127.0.0.1:8080',
        paths: Tuple[str] = ('/ipns/standard-template-construct.org/data/nexus_science/',),
        cache_size: int = 256 * 1024 * 1024,
    ):
        self.ipfs_http_endpoint = ipfs_http_endpoint
        self.paths = [path.rstrip('/') + '/' for path in paths]
        self.cache_size = cache_size
        self.index_registry = summa_embed.IndexRegistry()
        self.descriptions = {}

    async def setup(self):
        for path in self.paths:
            full_path = self.ipfs_http_endpoint + path
            headers_template = {"range": "bytes={start}-{end}"}
            if host_header := await detect_host_header(full_path):
                headers_template['host'] = host_header
            description = await self.index_registry.add({'config': {'remote': {
                'method': 'GET',
                'url_template': f'{full_path}{{file_name}}',
                'headers_template': headers_template,
                'cache_config': {'cache_size': self.cache_size},
            }}})
            self.descriptions[description['default_index_name']] = description
        return self.descriptions

    async def search(self, query: List[dict]):
        return await self.index_registry.search(query)
