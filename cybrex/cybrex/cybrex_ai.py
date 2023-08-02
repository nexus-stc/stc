import asyncio
import base64
import io
import json
import logging
import os.path
import uuid
from gzip import GzipFile
from typing import List, Optional

import chromadb
import numpy as np
import pypdf
import yaml
from aiokit import AioThing
from bs4 import BeautifulSoup
from izihawa_configurator import Configurator
from izihawa_utils.exceptions import BaseError
from izihawa_utils.file import mkdir_p
from langchain.chains.summarize import load_summarize_chain
from langchain.schema import Document
from stc_geck.advices import get_documents_on_topic
from stc_geck.client import StcGeck

from .models import CybrexModel


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

        self.db = chromadb.PersistentClient(path=os.path.join(self.home_path, 'chroma'))
        self.collection_name = self.model.get_embeddings_id()

        self.collection = self.db.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.model.embedder.embed_documents,
        )
        self.geck = geck
        if not self.geck:
            self.geck = StcGeck(
                ipfs_http_base_url=config['ipfs']['http']['base_url'],
                grpc_api_endpoint=config['summa']['endpoint']
            )
            self.starts.append(self.geck)

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

    async def generate_chunks_from_document(self, document):
        doi = document['doi']
        content = await self.resolve_document_content(document)
        if not content:
            return

        abstract = document.get('abstract', '')

        logging.getLogger('statbox').info({
            'action': 'chunking',
            'doi': doi,
        })

        extracted_texts = []

        abstract_soup = BeautifulSoup(abstract, features='lxml')
        content_soup = BeautifulSoup(content, features='lxml')

        for section_id, section in enumerate(list(abstract_soup.children) + list(content_soup.children)):
            for el in list(section.find_all()):
                if el.name in {'ref', 'formula', 'math', 'figure'}:
                    el.extract()
            text = section.get_text(' ', strip=True)
            if len(text) < 128:
                continue
            extracted_texts.append(text)

        metadatas = []
        texts = []

        for chunk_id, chunk in enumerate(self.model.text_splitter.split_text('\n\n'.join(extracted_texts))):
            if len(chunk) < 128:
                continue
            texts.append(chunk)
            metadatas.append({
                'doi': doi,
                'length': len(chunk),
                'chunk_id': chunk_id,
            })
        return metadatas, texts

    async def _get_missing_documents_chunks(self, documents: List[dict], skip_downloading_pdf: bool = True):
        metadatas = []
        texts = []
        for document in documents:
            doi = document['doi']
            if self.collection.get(where={'doi': doi})['documents']:
                logging.getLogger('statbox').info({
                    'action': 'already_stored',
                    'doi': doi,
                })
                continue
            if skip_downloading_pdf and 'content' not in document:
                logging.getLogger('statbox').info({
                    'action': 'no_content',
                    'doi': doi,
                })
                continue
            logging.getLogger('statbox').info({
                'action': 'retrieve_content',
                'doi': doi,
            })
            document_metadatas, document_texts = await self.generate_chunks_from_document(document)
            metadatas.extend(document_metadatas)
            texts.extend(document_texts)
        return metadatas, texts

    async def add_full_documents(self, documents: List[dict], skip_downloading_pdf: bool = True):
        if not documents:
            return
        metadatas, texts = await self._get_missing_documents_chunks(documents, skip_downloading_pdf=skip_downloading_pdf)
        if texts:
            logging.getLogger('statbox').info({
                'action': 'add_full_documents',
                'n': len(texts),
            })
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.collection.upsert(
                    documents=texts,
                    metadatas=metadatas,
                    ids=[str(uuid.uuid1()) for _ in range(len(texts))]
                )
            )
            logging.getLogger('statbox').info({
                'action': 'added_full_documents',
                'n': len(texts),
            })

    async def add_full_document_by_field_value(self, field, value) -> List[Document]:
        documents = await self.geck.get_summa_client().search_documents([{
            'index_alias': 'nexus_science',
            'collectors': [{'top_docs': {'limit': 1}}],
            'query': {'term': {'field': field, 'value': value}}
        }])
        if not documents:
            raise DocumentNotFoundError(**{field: value})
        await self.add_full_documents(documents)
        documents = [Document(page_content=text) for text in self.collection.get(where={field: value})['documents']]
        return documents

    async def dump_texts(self, query: str, output_path: str, n_summa_documents: int, skip_downloading_pdf: bool = True):
        documents = await self.keywords_search(query, n_summa_documents=n_summa_documents)
        metadatas, texts = await self._get_missing_documents_chunks(
            documents,
            skip_downloading_pdf=skip_downloading_pdf,
        )
        with GzipFile(output_path, mode='wb') as zipper:
            zipper.writelines([
                json.dumps({'metadata': metadata, 'text': text}).encode() + b'\n'
                for metadata, text in zip(metadatas, texts)
            ])

    async def import_texts(self, input_path: str):
        metadatas = []
        texts = []
        embeddings = []
        with GzipFile(input_path, mode='rb') as zipper:
            for line in zipper.readlines():
                processed_document = json.loads(line)
                doi = processed_document['metadata']['doi']
                if self.collection.get(where={'doi': doi})['documents']:
                    logging.getLogger('statbox').info({
                        'action': 'already_stored',
                        'doi': doi,
                    })
                    continue
                metadatas.append(processed_document['metadata'])
                texts.append(processed_document['text'])
                embedding = base64.b64decode(processed_document['embedding'])
                embedding = [n.item() for n in np.frombuffer(embedding, dtype=np.float64)]
                embeddings.append(embedding)

        if texts:
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.collection.upsert(
                    documents=texts,
                    metadatas=metadatas,
                    embeddings=embeddings,
                    ids=[str(uuid.uuid1()) for _ in range(len(texts))]
                )
            )

    async def chat_document(self, field, value, query, n_results: int):
        await self.add_full_document_by_field_value(field, value)

        documents = await self._query(query, n_results, where={field: value})
        result = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: self.model.llm.ask_documents(query, documents),
        )

        return result

    async def chat_science(self, query: str, n_results: int, n_summa_documents: int):
        full_documents = await self.keywords_search(query, n_summa_documents)

        await self.add_full_documents(full_documents)

        documents = await self._query(query, n_results)
        answer = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: self.model.llm.ask_documents(query, documents),
        )

        return answer, documents, await self.get_summa_documents_from_documents(documents)

    async def _query(self, query: str, n_results: int = 3, where: Optional[dict] = None):
        logging.getLogger('statbox').info({
            'action': 'query',
            'query': query,
            'n_results': n_results,
            'where': where,
        })
        response = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: self.collection.query(
                query_embeddings=[self.model.embedder.embed_query(query)],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances'],
                where=where,
            )
        )
        documents = []
        for (text, metadata, distance) in zip(response['documents'][0], response['metadatas'][0], response['distances'][0]):
            documents.append({'text': text, 'metadata': metadata, 'distance': distance})
        return documents

    async def keywords_search(self, query: str, n_summa_documents: int):
        if not n_summa_documents:
            return []
        logging.getLogger('statbox').info({
            'action': 'extract_keywords',
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
            'keywords': keywords,
        })
        topic = ' '.join(map(lambda x: x[0], filter(lambda x: x[1] > 0.5, keywords)))
        documents = await get_documents_on_topic(
            summa_client=self.geck.get_summa_client(),
            topic=topic,
            documents=n_summa_documents,
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

    async def semantic_search(self, query: str, n_results: int = 10, n_summa_documents: int = 30):
        full_documents = await self.keywords_search(query, n_summa_documents)
        await self.add_full_documents(full_documents)
        return await self._query(query, n_results)

    async def summarize_document(self, field, value):
        documents = await self.add_full_document_by_field_value(field, value)
        chain = load_summarize_chain(llm=self.model.llm, chain_type="map_reduce")
        result = chain.run(documents)
        return result.strip()
