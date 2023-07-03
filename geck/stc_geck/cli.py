#!/usr/bin/env python3
import json
import logging
import os.path
import sys

import fire
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
        ipfs_http_endpoint: str,
        ipfs_data_directory: str,
        index_alias: str,
        grpc_api_endpoint: str,
        embed: bool,
        timeout: int,
    ):
        self.geck = StcGeck(
            ipfs_http_base_url=ipfs_http_endpoint,
            ipfs_data_directory=ipfs_data_directory,
            index_aliases=(index_alias,),
            grpc_api_endpoint=grpc_api_endpoint,
            embed=embed,
        )
        self.index_alias = index_alias
        self.timeout = timeout

    async def search(self, query: str, limit: int = 1):
        """
        Searches in STC using default Summa match queries.
        Examples: `doi:10.1234/abc, isbns:9781234567890, "fetal hemoglobin"`

        :param query: query in Summa match format
        :param limit: how many results to return, higher values incurs LARGE performance penalty.

        :return: metadata records
        """
        print(f"{colored('INFO', 'green')}: Setting up indices: {self.index_alias}...")
        async with self.geck as geck:
            print(f"{colored('INFO', 'green')}: Searching {query}...")
            response = await geck.get_summa_client().search([{
                "index_alias": self.index_alias,
                "query": {
                    "match": {"value": query}
                },
                "collectors": [{"top_docs": {"limit": limit}}],
                "is_fieldnorms_scoring_enabled": False,
            }])
            documents = list(map(lambda x: json.loads(x.document), response.collector_outputs[0].documents.scored_documents))
            return documents

    async def documents(self):
        """
        Stream all STC documents.

        :return: metadata records
        """
        print(f"{colored('INFO', 'green')}: Setting up indices: {self.index_alias}...")
        async with self.geck as geck:
            async for document in geck.get_summa_client().documents(self.index_alias):
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
                data = await self.geck.download(results[0]["cid"], self.timeout)
                final_file_name = output_path + '.' + output_path_ext
                with open(final_file_name, 'wb') as f:
                    f.write(data)
                    f.close()
                    print(f"{colored('INFO', 'green')}: File {final_file_name} is written")
            else:
                print(f"{colored('ERROR', 'red')}: Not found CID for {query}", file=sys.stderr)
        else:
            print(f"{colored('ERROR', 'red')}: Not found {query}", file=sys.stderr)

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
        print(f"{colored('INFO', 'green')}: Setting up indices: {self.index_alias}...")
        async with self.geck as geck:
            return await geck.create_ipfs_directory(self.index_alias, output_car, query, limit, name_template)


async def stc_geck_cli(
    ipfs_http_endpoint: str = 'http://127.0.0.1:8080',
    ipfs_data_directory: str = '/ipns/standard-template-construct.org/data/',
    index_alias: str = 'nexus_science',
    grpc_api_endpoint: str = '127.0.0.1:37082',
    embed: bool = True,
    timeout: int = 600,
    debug: bool = False,
):
    """
    :param ipfs_http_endpoint: IPFS HTTP API Endpoint
    :param ipfs_data_directory: path to the directory with index
    :param index_alias: `nexus_free` (non-classified content) or `nexus_science` (similar to Crossref)
    :param grpc_api_endpoint: port used for Summa
    :param embed: setup embedded Summa server
    :param timeout: timeout for requests to IPFS
    :param debug: add debugging output
    :return:
    """
    logging.basicConfig(stream=sys.stdout, level=logging.INFO if debug else logging.ERROR)
    stc_geck_client = StcGeckCli(
        ipfs_http_endpoint=ipfs_http_endpoint,
        ipfs_data_directory=ipfs_data_directory,
        index_alias=index_alias,
        grpc_api_endpoint=grpc_api_endpoint,
        embed=embed,
        timeout=timeout,
    )
    return {
        'search': stc_geck_client.search,
        'download': stc_geck_client.download,
        'documents': stc_geck_client.documents,
        'create-ipfs-directory': stc_geck_client.create_ipfs_directory,
    }


def main():
    fire.Fire(stc_geck_cli, name='geck')


if __name__ == '__main__':
    main()
