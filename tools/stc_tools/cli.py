#!/usr/bin/env python3
import json

import aiohttp
import fire
from stc_tools.client import StcTools


class ItemNotFound(Exception):
    def __init__(self, query):
        self.query = query

    def __str__(self):
        return f'ItemNotFound(query="{self.query}")'


class CidNotFound(Exception):
    def __init__(self, query):
        self.query = query

    def __str__(self):
        return f'CidNotFound(query="{self.query}")'


class StcCliTools(StcTools):
    async def search(self, query: str, index_name: str = 'nexus_science', limit: int = 1, default_fields = ('title', 'abstract',)):
        """
        Searches in STC using default Summa match queries.
        Examples: `doi:10.1234/abc, isbns:9781234567890, "fetal hemoglobin"`

        :param query: query in Summa match format
        :param limit: how many results to return, higher values incurs LARGE performance penalty.
        :return: metadata records
        """
        print(f'Setting up index {self.path}...')
        await self.setup()
        print(f'Searching {query}...')
        response = await super().search([{
            "index_alias": index_name,
            "query": {"query": {"match": {"value": query, "default_fields": default_fields, 'field_boosts': {}}}},
            "collectors": [{"collector": {"top_docs": {"limit": limit}}}]
        }])
        return list(map(lambda x: json.loads(x['document']), response[0]['collector_output']['documents']['scored_documents']))

    async def download(self, query: str, output_path: str, index_name: str = 'nexus_science'):
        """
        Download file from STC using default Summa match queries.
        Examples: `doi:10.1234/abc, isbns:9781234567890`

        :param query: query in Summa match format
        :param output_path: filepath for writing file
        :return: file if record has corresponding CID
        """
        results = await self.search(query, index_name=index_name)
        if results:
            print(f'Found {query}')
            if 'cid' in results[0]:
                print(f'Receiving file...')
                async with aiohttp.ClientSession() as session:
                    async with session.get(f'{self.ipfs_http_endpoint}/ipfs/{results[0]["cid"]}') as resp:
                        data = await resp.read()
                        with open(output_path, 'wb') as f:
                            f.write(data)
                            f.close()
                            print(f'File {output_path} is written')
            else:
                print(f'Not found CID for {query}')
        else:
            print(f'Not found {query}')


async def stc_tools_cli(
    ipfs_http_endpoint: str = 'http://127.0.0.1:8080',
    paths: tuple[str] = ('/ipns/standard-template-construct.org/data/nexus_science/',),
):
    stc_tools_client = StcCliTools(ipfs_http_endpoint, paths)
    return {
        'search': stc_tools_client.search,
        'download': stc_tools_client.download,
    }


def main():
    fire.Fire(stc_tools_cli, name='stc-tools')


if __name__ == '__main__':
    main()
