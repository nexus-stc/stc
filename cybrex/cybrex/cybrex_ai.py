import asyncio
import base64
import io
import json
import logging
import os.path
from gzip import GzipFile
from typing import (
    List,
    Optional,
)

import numpy as np
import pypdf
import yaml
from aiokit import AioThing
from izihawa_configurator import Configurator
from izihawa_utils.exceptions import BaseError
from izihawa_utils.file import mkdir_p
from stc_geck.advices import get_documents_on_topic
from stc_geck.client import StcGeck

from .chains.map_reduce import (
    QAChain,
    SummarizeChain,
)
from .document_chunker import DocumentChunker
from .models import CybrexModel
from .vector_storage.chroma import ChromaVectorStorage


class DocumentNotFoundError(BaseError):
    pass


def print_color(text, color):
    print("\033[38;5;{}m{}\033[0m".format(color, text))


def default_config():
    return {
        'ipfs': {
            'http': {
                'base_url': 'http://127.0.0.1:8080'
            }
        },
        'model': CybrexModel.default_config(),
        'summa': {
            'endpoint': '127.0.0.1:10082'
        },
    }


class CybrexAI(AioThing):
    def __init__(
        self,
        home_path: Optional[str] = None,
        geck: Optional[StcGeck] = None,
    ):
        super().__init__()

        if home_path is None:
            home_path = os.environ.get("CYBREX_HOME", "~/.cybrex")
        self.home_path = os.path.expanduser(home_path)
        if not os.path.exists(self.home_path):
            mkdir_p(self.home_path)

        config_path = os.path.join(self.home_path, 'config.yaml')
        if not os.path.exists(config_path):
            with open(config_path, 'w') as f:
                f.write(yaml.dump(default_config(), default_flow_style=False))
        config = Configurator(configs=[
            config_path,
        ])

        self.model = CybrexModel(config['model'])
        self.document_chunker = DocumentChunker(text_splitter=self.model.text_splitter)

        self.geck = geck
        if not self.geck:
            self.geck = StcGeck(
                ipfs_http_base_url=config['ipfs']['http']['base_url'],
                grpc_api_endpoint=config['summa']['endpoint']
            )
            self.starts.append(self.geck)

        self.vector_storage = ChromaVectorStorage(
            path=os.path.join(self.home_path, 'chroma'),
            collection_name=self.model.get_embeddings_id(),
        )

    async def resolve_document_content(self, document: dict) -> Optional[str]:
        if 'content' in document:
            return document['content']
        elif 'links' in document:
            primary_link = document['links'][0]
            file_content = await self.geck.download(document['links'][0]['cid'])
            match primary_link['type']:
                case 'pdf':
                    pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
                    return '\n'.join(page.extract_text() for page in pdf_reader.pages)
                case _:
                    raise RuntimeError("Unsupported extension")

    async def generate_chunks_from_document(self, document: dict) -> List[dict]:
        document['content'] = await self.resolve_document_content(document)
        return self.document_chunker.to_chunks(document)

    async def _get_missing_chunks(self, documents: List[dict], skip_downloading_pdf: bool = True) -> List[dict]:
        chunks = []
        for document in documents:
            doi = document['doi']
            if await self.vector_storage.get_by_field_value('doi', doi):
                logging.getLogger('statbox').info({
                    'action': 'already_stored',
                    'mode': 'cybrex',
                    'doi': doi,
                })
                continue
            if skip_downloading_pdf and 'content' not in document:
                logging.getLogger('statbox').info({
                    'action': 'no_content',
                    'mode': 'cybrex',
                    'doi': doi,
                })
                continue
            logging.getLogger('statbox').info({
                'action': 'retrieve_content',
                'mode': 'cybrex',
                'doi': doi,
            })
            document_chunks = await self.generate_chunks_from_document(document)
            chunks.extend(document_chunks)
        return chunks

    async def add_full_documents(self, documents: List[dict], skip_downloading_pdf: bool = True):
        if not documents:
            return
        chunks = await self._get_missing_chunks(documents, skip_downloading_pdf=skip_downloading_pdf)
        if chunks:
            logging.getLogger('statbox').info({
                'action': 'add_full_documents',
                'mode': 'cybrex',
                'n': len(chunks),
            })
            await self.vector_storage.upsert(chunks)
            logging.getLogger('statbox').info({
                'action': 'added_full_documents',
                'mode': 'cybrex',
                'n': len(chunks),
            })

    async def add_full_document_by_field_value(self, field, value) -> List[dict]:
        documents = await self.geck.get_summa_client().search_documents([{
            'index_alias': 'nexus_science',
            'collectors': [{'top_docs': {'limit': 1}}],
            'query': {'term': {'field': field, 'value': value}}
        }])
        if not documents:
            raise DocumentNotFoundError(**{field: value})
        await self.add_full_documents(documents)
        return await self.vector_storage.get_by_field_value(field, value)

    async def export_chunks(self, query: str, output_path: str, n_documents: int, skip_downloading_pdf: bool = True):
        documents = await self.keywords_search(query, n_documents=n_documents)
        chunks = await self._get_missing_chunks(
            documents,
            skip_downloading_pdf=skip_downloading_pdf,
        )
        with GzipFile(output_path, mode='wb') as zipper:
            zipper.writelines([
                json.dumps(chunk).encode() + b'\n'
                for chunk in chunks
            ])

    async def import_chunks(self, input_path: str):
        chunks = []
        with GzipFile(input_path, mode='rb') as zipper:
            for line in zipper.readlines():
                chunk = json.loads(line)
                doi = chunk['metadata']['doi']
                if await self.vector_storage.get_by_field_value('doi', doi):
                    logging.getLogger('statbox').info({
                        'action': 'already_stored',
                        'mode': 'cybrex',
                        'doi': doi,
                    })
                    continue
                chunk['embedding'] = base64.b64decode(chunk['embedding'])
                chunk['embedding'] = [n.item() for n in np.frombuffer(chunk['embedding'], dtype=np.float64)]
                chunks.append(chunk)

        if chunks:
            await self.vector_storage.upsert(chunks)

    async def chat_document(self, field, value, query, n_chunks: int):
        await self.add_full_document_by_field_value(field, value)

        documents = await self._query(query, n_chunks, where={field: value})
        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: self.model.llm.ask_documents(query, documents),
        )

        return result

    async def chat_science(self, query: str, n_chunks: int, n_documents: int, semantic_threshold: float = 0.5):
        full_documents = await self.keywords_search(query, n_documents)

        await self.add_full_documents(full_documents)

        chunks = await self._query(query, n_chunks, semantic_threshold=semantic_threshold)
        chain = QAChain(query=query, llm=self.model.llm)
        answer = chain.process(chunks)

        return answer, chunks, await self.get_summa_documents_from_documents(chunks)

    async def _query(self, query: str, n_chunks: int = 3, where: Optional[dict] = None, semantic_threshold: float = 0.5):
        logging.getLogger('statbox').info({
            'action': 'query',
            'mode': 'cybrex',
            'query': query,
            'n_chunks': n_chunks,
            'where': where,
        })
        chunks = await self.vector_storage.query([self.model.embedder.embed_query(query)], n_chunks=n_chunks, where=where)
        chunks = chunks[0]
        filtered_chunks = []
        for chunk in chunks:
            if chunk['distance'] < semantic_threshold:
                filtered_chunks.append(chunk)
        logging.getLogger('statbox').info({
            'action': 'query',
            'mode': 'cybrex',
            'found': len(filtered_chunks),
            'semantic_threshold': semantic_threshold,
        })
        return filtered_chunks

    async def keywords_search(self, query: str, n_documents: int):
        if not n_documents:
            return []
        logging.getLogger('statbox').info({
            'action': 'extract_keywords',
            'mode': 'cybrex',
            'query': query,
        })
        keywords = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: self.model.keyword_extractor.extract_keywords(
                query,
                keyphrase_ngram_range=(1, 1),
            )
        )
        logging.getLogger('statbox').info({
            'action': 'extracted_keywords',
            'mode': 'cybrex',
            'keywords': keywords,
        })
        topic = ' '.join(map(lambda x: x[0], filter(lambda x: x[1] > 0.5, keywords)))
        documents = await get_documents_on_topic(
            summa_client=self.geck.get_summa_client(),
            topic=topic,
            documents=n_documents,
        )
        return documents

    async def get_summa_documents_from_documents(self, documents):
        dois = set([document['metadata']['doi'] for document in documents])
        _summa_documents = await asyncio.gather(*[
            self.geck.get_summa_client().search_documents([{
                'index_alias': 'nexus_science',
                'query': {'term': {'field': 'doi', 'value': doi}},
                'collectors': [{'top_docs': {'limit': 100}}],
            }])
            for doi in dois
        ])
        summa_documents = []
        for summa_document in _summa_documents:
            summa_documents.append(summa_document[0])
        return summa_documents

    async def semantic_search(self, query: str, n_chunks: int = 10, n_documents: int = 30):
        documents = await self.keywords_search(query, n_documents)
        await self.add_full_documents(documents)
        return await self._query(query, n_chunks)

    async def summarize_document(self, field, value):
        chunks = await self.add_full_document_by_field_value(field, value)
        chain = SummarizeChain(llm=self.model.llm)
        result = chain.process(chunks)
        return result.strip()
