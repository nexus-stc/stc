import dataclasses
import logging
import random
import typing

from aiobaseclient import BaseClient
from aiobaseclient.exceptions import ServiceUnavailableError
from aiohttp import ClientPayloadError


@dataclasses.dataclass
class NamedCid:
    name: str
    cid: str
    size: int


def select_elements_with_weights(lst, weights, k):
    if k > len(lst):
        raise ValueError("k must be less than or equal to the length of lst.")
    if len(weights) != len(lst):
        raise ValueError("weights must have the same length as lst.")
    selected_indices = set()
    while len(selected_indices) < k:
        index = random.choices(range(len(lst)), weights=weights)[0]
        selected_indices.add(index)
    selected_elements = [lst[i]['peer_id'] for i in selected_indices]
    return selected_elements


class IpfsClusterClient(BaseClient):
    def __init__(self, base_url: str, peers, **kwargs):
        super().__init__(base_url, **kwargs)
        self.peers = peers or []
        self.weights = list(map(lambda x: x['weight'], self.peers))

    async def response_processor(self, response):
        return response

    def get_allocations(self, k):
        if self.peers:
            return select_elements_with_weights(self.peers, weights=self.weights, k=k)

    async def add(self, car_data, name, k):
        allocations = self.get_allocations(k)
        logging.getLogger('statbox').info({
            'action': 'pinning',
            'mode': 'integral',
            'name': name,
            'k': k,
            'len': len(car_data)
        })
        if allocations:
            response = await self.post(
                f"/add?format=car&name={name}&user-allocations={','.join(allocations)}",
                data={'file': car_data}
            )
        else:
            response = await self.post(
                f"/add?format=car&name={name}",
                data={'file': car_data}
            )
        assert response.status == 200
        json_response = await response.json()
        assert json_response is not None
        logging.getLogger('statbox').info({
            'action': 'pinned',
            'mode': 'integral',
            'name': name,
            'response': json_response,
            'status': response.status
        })
        return json_response

    async def pin_rm(self, cid):
        logging.getLogger('statbox').info({
            'action': 'pin_rm',
            'mode': 'integral',
            'cid': cid,
        })
        response = await self.delete(
            f"/pins/{cid}",
        )
        response = await response.json()
        logging.getLogger('statbox').info({
            'action': 'removed',
            'mode': 'integral',
            'cid': cid,
            'response': response
        })
        return response

    async def pin_ls(self, cid):
        response = await self.get(
            f"/allocations/{cid}",
        )
        if response.status == 404:
            return
        response = await response.json()
        return response


class IpfsHttpClient(BaseClient):
    async def response_processor(self, response):
        if response.status != 200:
            raise ServiceUnavailableError()
        return response

    async def get_iter(self, cid):
        resp = await self.get(f'/ipfs/{cid}')
        try:
            async for data, _ in resp.content.iter_chunks():
                yield data
        except ClientPayloadError:
            raise ServiceUnavailableError()

    async def get_item(self, cid):
        resp = await self.get(f'/ipfs/{cid}')
        return await resp.read()


class IpfsApiClient(IpfsHttpClient):
    async def add(self, data, hash_name='blake3', chunker='size-1048576'):
        logging.getLogger('statbox').info({
            'action': 'hashing_data',
            'file_length': len(data),
            'mode': 'ipfs_api_client',
        })
        response = await self.post(
            f'/api/v0/add?arg=file&chunker={chunker}&hash={hash_name}&pin=false',
            data={'file': data},
        )
        response = await response.json()
        return response['Hash']

    async def export_dag(self, file_hash):
        logging.getLogger('statbox').info({
            'action': 'exporting_dag',
            'mode': 'ipfs_api_client',
            'file_hash': file_hash,
        })
        response = await self.post(f"/api/v0/dag/export?arg={file_hash}")
        return await response.read()

    async def ls(self, cid, size=True, resolve_type=True):
        logging.getLogger('statbox').info({
            'action': 'ls',
            'mode': 'ipfs_api_client',
            'cid': cid,
        })
        response = await self.post(f'/api/v0/ls?arg={cid}&size={size}&resolve-type={resolve_type}')
        return await response.json()

    async def walk_ipfs_directory(self, cid, recursive=True, size=True, resolve_type=True) -> typing.AsyncIterable[NamedCid]:
        directory_content = await self.ls(cid, size=size, resolve_type=resolve_type)
        for entry in directory_content['Objects']:
            for link in entry['Links']:
                if link['Type'] == 2 or not resolve_type:
                    yield NamedCid(name=link['Name'], cid=link['Hash'], size=link['Size'])
                elif (link['Type'] == 1 or link['Type'] == 5) and recursive:
                    async for item in self.walk_ipfs_directory(link['Hash']):
                        yield item

    async def get_item(self, cid):
        resp = await self.post(f'/api/v0/get?arg={cid}')
        return await resp.read()
