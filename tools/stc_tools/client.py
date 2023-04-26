import re
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
        path: str = '/ipns/standard-template-construct.org/data/nexus_science/',
    ):
        self.ipfs_http_endpoint = ipfs_http_endpoint
        self.path = path.rstrip('/') + '/'
        self.index_registry = summa_embed.IndexRegistry()
        self.description = None

    async def setup(self):
        full_path = self.ipfs_http_endpoint + self.path
        headers_template = {"range": "bytes={start}-{end}"}
        if host_header := await detect_host_header(full_path):
            headers_template['host'] = host_header
        self.description = await self.index_registry.add({'config': {'remote': {
            'method': 'GET',
            'url_template': f'{full_path}{{file_name}}',
            'headers_template': headers_template,
        }}})

    async def search(self, query: dict):
        return await self.index_registry.search(query)
