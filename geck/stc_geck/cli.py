#!/usr/bin/env python3
import asyncio
import functools
import logging
import os.path
import sys
from typing import (
    List,
    Optional,
)

import fire
import humanfriendly
from termcolor import colored

from .client import StcGeck
from .exceptions import IpfsConnectionError


def exception_handler(func):
    @functools.wraps(func)
    async def wrapper_func(self, *args, **kwargs):
        try:
            await func(self, *args, **kwargs)
        except IpfsConnectionError as e:
            print(
                f"{colored('ERROR', 'red')}: Cannot connect to IPFS: {e.info}\n"
                f"{colored('HINT', 'yellow')}: Try to pass working IPFS address with `--ipfs-http-base-url` parameter",
                file=sys.stderr,
            )
        finally:
            await self.geck.stop()
    return wrapper_func


class StcGeckCli:
    def __init__(
        self,
        ipfs_http_base_url: str,
        ipfs_api_base_url: str,
        ipfs_data_directory: str,
        grpc_api_endpoint: str,
        index_alias: str,
        timeout: int,
    ):
        self.geck = StcGeck(
            ipfs_http_base_url=ipfs_http_base_url,
            ipfs_api_base_url=ipfs_api_base_url,
            ipfs_data_directory=ipfs_data_directory,
            grpc_api_endpoint=grpc_api_endpoint,
            index_alias=index_alias,
            timeout=timeout,
        )
        self.grpc_api_endpoint = grpc_api_endpoint
        self.index_alias = index_alias

    def prompt(self):
        if self.geck.is_embed:
            print(f"{colored('INFO', 'green')}: Setting up indices...", file=sys.stderr)
        else:
            print(f"{colored('INFO', 'green')}: Using existent instance on {self.geck.grpc_api_endpoint}", file=sys.stderr)

    @exception_handler
    async def documents(self, query_filter: Optional[dict] = None, fields: Optional[List[str]] = None):
        """
        Stream all STC chunks.

        :return: metadata records
        """
        self.prompt()
        async with self.geck as geck:
            async for document in geck.get_summa_client().documents(
                self.index_alias,
                query_filter=query_filter,
                fields=fields,
            ):
                print(document)

    @exception_handler
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
            print(f"{colored('INFO', 'green')}: Found {query}", file=sys.stderr)
            if 'cid' in results[0]:
                print(f"{colored('INFO', 'green')}: Receiving file {query}...", file=sys.stderr)
                if (real_extension := results[0].get('extension', 'pdf')) != output_path_ext:
                    print(
                        f"{colored('WARN', 'yellow')}: Receiving file extension `{real_extension}` "
                        f"is not matching with your output path extension `{output_path_ext}`. Changed to correct one.",
                        file=sys.stderr
                    )
                    output_path_ext = real_extension
                data = await self.geck.download(results[0]["cid"])
                final_file_name = output_path + '.' + output_path_ext
                with open(final_file_name, 'wb') as f:
                    f.write(data)
                    f.close()
                    print(f"{colored('INFO', 'green')}: File {final_file_name} is written", file=sys.stderr)
            else:
                print(f"{colored('ERROR', 'red')}: Not found CID for {query}", file=sys.stderr)
        else:
            print(f"{colored('ERROR', 'red')}: Not found {query}", file=sys.stderr)

    @exception_handler
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
        self.prompt()
        async with self.geck as geck:
            return await geck.random_cids(n=n)

    async def search(self, query: str, limit: int = 1, offset: int = 0):
        """
        Searches in STC using default Summa match queries.
        Examples: `doi:10.1234/abc, isbns:9781234567890, "fetal hemoglobin"`

        :param query: query in Summa match format
        :param limit: how many results to return, higher values incurs LARGE performance penalty.
        :param offset:

        :return: metadata records
        """
        self.prompt()
        async with self.geck as geck:
            print(f"{colored('INFO', 'green')}: Searching {query}...", file=sys.stderr)
            logging.getLogger('statbox').info({'action': 'search', 'query': query})
            summa_client = geck.get_summa_client()
            query = {
                'index_alias': self.index_alias,
                'query': {'match': {'value': query.lower()}},
                'collectors': [{'top_docs': {'limit': limit, 'offset': offset}}],
                'is_fieldnorms_scoring_enabled': False,
            }
            return await summa_client.search_documents(query)

    async def serve(self):
        """
        Start serving Summa
        """
        self.prompt()
        async with self.geck:
            print(f"{colored('INFO', 'green')}: Serving on {self.grpc_api_endpoint}", file=sys.stderr)
            while True:
                await asyncio.sleep(5)

    @exception_handler
    async def create_ipfs_directory(
        self,
        output_car: str,
        query: str = None,
        limit: int = 100,
        name_template: str = '{id}.{extension}',
    ):
        """
        Stream all STC chunks.

        :return: metadata records
        """
        self.prompt()
        async with self.geck as geck:
            return await geck.create_ipfs_directory(output_car, query, limit, name_template)


async def stc_geck_cli(
    ipfs_http_base_url: str = 'http://127.0.0.1:8080',
    ipfs_api_base_url: str = 'http://127.0.0.1:5001',
    ipfs_data_directory: str = '/ipns/standard-template-construct.org/data',
    grpc_api_endpoint: str = '127.0.0.1:10082',
    index_alias: str = 'nexus_science',
    timeout: int = 120,
    debug: bool = False,
):
    """
    :param ipfs_http_base_url: IPFS HTTP Endpoint
    :param ipfs_api_base_url: IPFS HTTP API Endpoint
    :param ipfs_data_directory: path to the directory with index
    :param grpc_api_endpoint: port used for Summa
    :param index_alias: default index alias
    :param timeout: timeout for requests to IPFS
    :param debug: add debugging output
    :return:
    """
    logging.basicConfig(stream=sys.stdout, level=logging.INFO if debug else logging.ERROR)
    stc_geck_client = StcGeckCli(
        ipfs_http_base_url=ipfs_http_base_url,
        ipfs_api_base_url=ipfs_api_base_url,
        ipfs_data_directory=ipfs_data_directory,
        grpc_api_endpoint=grpc_api_endpoint,
        index_alias=index_alias,
        timeout=timeout,
    )
    return {
        'create-ipfs-directory': stc_geck_client.create_ipfs_directory,
        'documents': stc_geck_client.documents,
        'download': stc_geck_client.download,
        'random-cids': stc_geck_client.random_cids,
        'search': stc_geck_client.search,
        'serve': stc_geck_client.serve,
    }


def main():
    fire.Fire(stc_geck_cli, name='geck')


if __name__ == '__main__':
    main()
