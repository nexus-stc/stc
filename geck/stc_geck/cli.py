#!/usr/bin/env python3
import asyncio
import json
import logging
import os.path
import sys
from typing import Optional

import fire
import humanfriendly
from termcolor import colored

from .client import StcGeck


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


class StcGeckCli:
    def __init__(
        self,
        ipfs_http_base_url: str,
        ipfs_api_base_url: str,
        ipfs_data_directory: str,
        index_name: str,
        grpc_api_endpoint: str,
        timeout: int,
    ):
        self.geck = StcGeck(
            ipfs_http_base_url=ipfs_http_base_url,
            ipfs_api_base_url=ipfs_api_base_url,
            ipfs_data_directory=ipfs_data_directory,
            index_names=(index_name,),
            grpc_api_endpoint=grpc_api_endpoint,
            timeout=timeout,
        )
        self.grpc_api_endpoint = grpc_api_endpoint
        self.index_name = index_name

    async def documents(self):
        """
        Stream all STC documents.

        :return: metadata records
        """
        print(f"{colored('INFO', 'green')}: Setting up indices: {self.index_name}...")
        async with self.geck as geck:
            async for document in geck.get_summa_client().documents(self.index_name):
                print(document)

    async def download(self, query: str, output_path: str):
        """
        Download file from STC using default Summa match queries.
        Examples: `doi:10.1234/abc, isbns:9781234567890`

        :param query: query in Summa match format
        :param output_path: filepath for writing file

        :return: file if record has corresponding CID
        """
        results = await self.search(query)
        output_path, output_path_ext = os.path.splitext(output_path)
        output_path_ext = output_path_ext.lstrip('.')
        if results:
            print(f"{colored('INFO', 'green')}: Found {query}")
            if 'cid' in results[0]:
                print(f"{colored('INFO', 'green')}: Receiving file {query}...")
                if (real_extension := results[0].get('extension', 'pdf')) != output_path_ext:
                    print(
                        f"{colored('WARN', 'yellow')}: Receiving file extension `{real_extension}` "
                        f"is not matching with your output path extension `{output_path_ext}`. Changed to correct one.")
                    output_path_ext = real_extension
                data = await self.geck.download(results[0]["cid"])
                final_file_name = output_path + '.' + output_path_ext
                with open(final_file_name, 'wb') as f:
                    f.write(data)
                    f.close()
                    print(f"{colored('INFO', 'green')}: File {final_file_name} is written")
            else:
                print(f"{colored('ERROR', 'red')}: Not found CID for {query}", file=sys.stderr)
        else:
            print(f"{colored('ERROR', 'red')}: Not found {query}", file=sys.stderr)

    async def random_cids(self, n: Optional[int] = None, space: Optional[str] = None):
        """
        Return random CIDs for pinning from the STC Hub API.

        :param n: number of items to pin
        :param space: approximate disk space you would like to allocate for pinning
        """
        if not n and not space:
            raise ValueError("`n` or `space_bytes` should be set")
        if space:
            # 3.61MB is the average size of the item
            n = int(humanfriendly.parse_size(space) / (3.61 * 1024 * 1024))
        async with self.geck as geck:
            return await geck.random_cids(n=n)

    async def search(self, query: str, limit: int = 1):
        """
        Searches in STC using default Summa match queries.
        Examples: `doi:10.1234/abc, isbns:9781234567890, "fetal hemoglobin"`

        :param query: query in Summa match format
        :param limit: how many results to return, higher values incurs LARGE performance penalty.

        :return: metadata records
        """
        print(f"{colored('INFO', 'green')}: Setting up indices: {self.index_name}...")
        async with self.geck as geck:
            print(f"{colored('INFO', 'green')}: Searching {query}...")
            response = await geck.get_summa_client().search([{
                "index_alias": self.index_name,
                "query": {
                    "match": {"value": query}
                },
                "collectors": [{"top_docs": {"limit": limit}}],
                "is_fieldnorms_scoring_enabled": False,
            }])
            documents = list(map(lambda x: json.loads(x.document), response.collector_outputs[0].documents.scored_documents))
            return documents

    async def serve(self):
        """
        Start serving Summa
        """
        print(f"{colored('INFO', 'green')}: Setting up indices: {self.index_name}...")
        async with self.geck:
            print(f"{colored('INFO', 'green')}: Serving on {self.grpc_api_endpoint}")
            while True:
                await asyncio.sleep(5)

    async def create_ipfs_directory(
        self,
        output_car: str,
        query: str = None,
        limit: int = 100,
        name_template: str = '{id}.{extension}',
    ):
        """
        Stream all STC documents.

        :return: metadata records
        """
        print(f"{colored('INFO', 'green')}: Setting up indices: {self.index_name}...")
        async with self.geck as geck:
            return await geck.create_ipfs_directory(self.index_name, output_car, query, limit, name_template)


async def stc_geck_cli(
    ipfs_http_base_url: str = 'http://127.0.0.1:8080',
    ipfs_api_base_url: str = 'http://127.0.0.1:5001',
    ipfs_data_directory: str = '/ipns/standard-template-construct.org/data/',
    index_name: str = 'nexus_science',
    grpc_api_endpoint: str = '127.0.0.1:10082',
    timeout: int = 120,
    debug: bool = False,
):
    """
    :param ipfs_http_base_url: IPFS HTTP API Endpoint
    :param ipfs_data_directory: path to the directory with index
    :param index_name: `nexus_free` (non-classified content) or `nexus_science` (similar to Crossref)
    :param grpc_api_endpoint: port used for Summa
    :param timeout: timeout for requests to IPFS
    :param debug: add debugging output
    :return:
    """
    logging.basicConfig(stream=sys.stdout, level=logging.INFO if debug else logging.ERROR)
    stc_geck_client = StcGeckCli(
        ipfs_http_base_url=ipfs_http_base_url,
        ipfs_api_base_url=ipfs_api_base_url,
        ipfs_data_directory=ipfs_data_directory,
        index_name=index_name,
        grpc_api_endpoint=grpc_api_endpoint,
        timeout=timeout,
    )
    return {
        'create-ipfs-directory': stc_geck_client.create_ipfs_directory,
        'download': stc_geck_client.download,
        'documents': stc_geck_client.documents,
        'random-cids': stc_geck_client.random_cids,
        'search': stc_geck_client.search,
        'serve': stc_geck_client.serve,
    }


def main():
    fire.Fire(stc_geck_cli, name='geck')


if __name__ == '__main__':
    main()
