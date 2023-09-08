import fire
from aiobaseclient import BaseClient
from aiokit.utils import sync_fu
from izihawa_ipfs_api import IpfsHttpClient

from library.sciparse.sciparser import (
    ClientPool,
    SciParser,
)


async def process(grobid_base_url, ipfs_base_url, doi):
    ipfs_http_client = IpfsHttpClient(base_url=ipfs_base_url)
    await ipfs_http_client.start()
    grobid_client = BaseClient(base_url=grobid_base_url)
    await grobid_client.start()

    sci_parser = SciParser(
        ipfs_http_client=ipfs_http_client,
        grobid_pool=ClientPool.from_client(grobid_client, par=16),
    )
    await sci_parser.start()
    parsed_paper = await sci_parser.parse_paper(doi)
    print(parsed_paper)


def main():
    fire.Fire(sync_fu(process))


if __name__ == '__main__':
    main()
