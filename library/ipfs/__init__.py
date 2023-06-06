import logging
import random

from aiobaseclient import BaseClient
from aiobaseclient.exceptions import ServiceUnavailableError
from aiohttp import ClientPayloadError


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
        self.peers = peers
        self.weights = list(map(lambda x: x['weight'], self.peers))

    async def response_processor(self, response):
        return response

    def get_allocations(self, k):
        return select_elements_with_weights(self.peers, weights=self.weights, k=k)

    async def add(self, car_data, name, file_name, k):
        allocations = self.get_allocations(k)
        logging.getLogger('statbox').info({
            'action': 'pinning',
            'mode': 'integral',
            'name': name,
            'k': k,
            'file_name': file_name,
            'len': len(car_data)
        })
        response = await self.post(
            f"/add?format=car&name={name}&user-allocations={','.join(allocations)}",
            data={file_name: car_data}
        )
        response = await response.json()
        logging.getLogger('statbox').info({
            'action': 'pinned',
            'mode': 'integral',
            'file_name': file_name,
            'response': response
        })
        return response

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
    async def add(self, file_name, data):
        logging.getLogger('statbox').info({
            'action': 'hashing_data',
            'file_length': len(data),
            'mode': 'ipfs_api_client',
            'file_name': file_name,
        })
        response = await self.post(
            f'/api/v0/add?arg={file_name}&chunker=size-1048576&hash=blake3&pin=false',
            data={file_name: data},
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
