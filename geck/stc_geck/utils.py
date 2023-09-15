import asyncio
import logging
import os
import re
import socket
import tempfile
from urllib.parse import quote

import ipfs_hamt_directory_py

NON_ALNUMWHITESPACE_REGEX = re.compile(r'([^\s\w])+')
MULTIWHITESPACE_REGEX = re.compile(r"\s+")


def cast_string_to_single_string(s):
    processed = MULTIWHITESPACE_REGEX.sub(' ', NON_ALNUMWHITESPACE_REGEX.sub(' ', s))
    processed = processed.strip().replace(' ', '-')
    return processed


async def create_car(output_car, documents, limit, name_template) -> str:
    with tempfile.TemporaryDirectory() as td:
        input_data = os.path.join(td, 'input_data.txt')
        with open(input_data, 'wb') as f:
            async for document in documents:
                if limit <= 0:
                    break
                id_ = document.get('doi') or document.get('md5')
                item_name = name_template.format(
                    title=cast_string_to_single_string(document['title']) if 'title' in document else id_,
                    id=id_,
                    md5=document.get('md5'),
                    doi=document.get('doi'),
                    extension=document.get('metadata', {}).get('extension', 'pdf'),
                )
                f.write(quote(item_name, safe='').encode())
                f.write(b' ')
                f.write(document['cid'].encode())
                f.write(b' ')
                f.write(str(document.get('filesize') or 0).encode())
                f.write(b'\n')
                limit -= 1
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: ipfs_hamt_directory_py.from_file(input_data, output_car, td),
        )


def is_endpoint_listening(endpoint):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ip, port = endpoint.split(':')
    try:
        is_open = sock.connect_ex((ip, int(port))) == 0
        sock.close()
        return is_open
    except socket.gaierror as e:
        logging.getLogger('warning').warning({'action': 'warning', 'error': str(e)})
        return False
