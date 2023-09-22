import asyncio
import base64
import io
import json
import logging
import os.path
from gzip import GzipFile
from typing import (
    List,
    Literal,
    Optional,
)

import numpy as np
import pypdf
import yaml
from aiokit import AioThing
from izihawa_configurator import Configurator
from izihawa_utils.exceptions import BaseError
from izihawa_utils.file import mkdir_p
from stc_geck.advices import BaseDocumentHolder
from stc_geck.client import StcGeck

from .chains.map_reduce import (
    QAChain,
    SummarizeChain,
)
from .data_source.base import SourceDocument
from .data_source.geck_data_source import GeckDataSource
from .document_chunker import DocumentChunker
from .model import CybrexModel
from .vector_storage.qdrant import QdrantVectorStorage


class DocumentNotFoundError(BaseError):
    pass


def print_color(text, color):
    print("\033[38;5;{}m{}\033[0m".format(color, text))


class CybrexAI(AioThing):
    def __init__(
        self,
        home_path: Optional[str] = None,
        geck: Optional[StcGeck] = None,
    ):
        """
        Main Cybrex class that manages AI operations

        :param home_path: path to config and/or embeddings directory
        :param geck: an instance of GECK
        """
        super().__init__()
        self.home_path = self.get_home_path(home_path)

        config_path = self.ensure_config()
        config = Configurator(configs=[
            config_path,
        ])

        self.model = CybrexModel(config['model'])
        self.document_chunker = DocumentChunker(
            text_splitter=self.model.text_splitter,
            add_metadata=self.model.config['text_splitter']['add_metadata'],
        )

        self.geck = geck
        if not self.geck:
            self.geck = StcGeck(
                ipfs_http_base_url=config['ipfs']['http']['base_url'],
                grpc_api_endpoint=config['summa']['endpoint'],
                timeout=600,
            )
            self.starts.append(self.geck)

        self.data_source = GeckDataSource(self.geck)
        self.vector_storage = QdrantVectorStorage(
            qdrant_config=config['qdrant'],
            collection_name=self.model.get_embeddings_id(),
            embedding_function=self.model.embed_documents,
            force_recreate=config['qdrant'].pop('force_recreate', False)
        )

    def get_home_path(self, home_path: str) -> str:
        """
        Expands path to config and/or embeddings directory and ensures the directory existence

        :param home_path:
        :return:
        """
        if home_path is None:
            home_path = os.environ.get("CYBREX_HOME", "~/.cybrex")
        home_path = os.path.expanduser(home_path)
        if not os.path.exists(home_path):
            mkdir_p(home_path)
        return home_path

    def ensure_config(
        self,
        ipfs_http_base_url: str = 'http://127.0.0.1:8080',
        summa_endpoint: str = '127.0.0.1:10082',
        qdrant_base_url: str = 'http://127.0.0.1',
        llm_name: Literal['llama-2-7b', 'llama-2-7b-uncensored', 'llama-2-13b', 'openai', 'petals-llama-2-70b'] = 'llama-2-7b-uncensored',
        embedder_name: Literal['instructor-xl', 'openai', 'bge-small-en'] = 'bge-small-en',
        device: str = 'cpu',
        gpu_layers: int = 50,
        force: bool = False,
    ):
        """
        Write config to $CYBREX_HOME/config.yaml
        :param ipfs_http_base_url: IPFS HTTP base url, i.e. `http://127.0.0.1:8080`
        :param summa_endpoint: Summa endpoint, i.e. `127.0.0.1:10082`
        :param qdrant_base_url:
        :param llm_name: 'llama-2-7b', 'llama-2-7b-uncensored', 'llama-2-13b', 'openai', 'petals-llama-2-70b'
        :param embedder_name: 'instructor-xl', 'openai', 'bge-small-en''
        :param device: 'cpu' or 'cuda'
        :param gpu_layers: number of layers to enabled offloading part of calculations to GPU
        :param force: overwrite even if config already exists
        :return:
        """
        config_path = os.path.join(self.home_path, 'config.yaml')
        if not os.path.exists(config_path) or force:
            config = {
                'ipfs': {
                    'http': {
                        'base_url': ipfs_http_base_url,
                    }
                },
                'model': CybrexModel.default_config(
                    llm_name=llm_name,
                    embedder_name=embedder_name,
                    device=device,
                    gpu_layers=gpu_layers,
                ),
                'qdrant': {
                    'url': qdrant_base_url,
                    'prefer_grpc': True,
                },
                'summa': {
                    'endpoint': summa_endpoint,
                },
            }
            with open(config_path, 'w') as f:
                f.write(yaml.dump(config, default_flow_style=False))
        return config_path

    async def resolve_document_content(self, document: SourceDocument) -> Optional[str]:
        """
        Retrieves document content from `content` field or from underlying PDF file.

        :param document:
        :return:
        """
        document = document.document
        if 'content' in document:
            return document['content']
        document_holder = BaseDocumentHolder(document)
        # ToDo: should also utilize epub links
        if pdf_link := document_holder.get_links().get_link_with_extension('pdf'):
            file_content = await self.geck.download(pdf_link['cid'])
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
            return '\n'.join(page.extract_text() for page in pdf_reader.pages)

    async def generate_chunks_from_document(self, document: SourceDocument) -> List[dict]:
        """
        Chunk documents using pre-configured chunker

        :param document:
        :return:
        """
        document.document['content'] = await self.resolve_document_content(document)
        return await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: self.document_chunker.to_chunks(document)
        )

    async def _get_missing_chunks(self, documents: List[SourceDocument], skip_downloading_pdf: bool = True) -> List[dict]:
        all_chunks = []
        for document in documents:
            is_stored = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.vector_storage.exists_by_field_value('document_id', document.document_id)
            )
            if is_stored:
                logging.getLogger('statbox').info({
                    'action': 'already_stored',
                    'mode': 'cybrex',
                    'document_id': document.document_id,
                })
                continue
            if skip_downloading_pdf and 'content' not in document.document:
                logging.getLogger('statbox').info({
                    'action': 'no_content',
                    'mode': 'cybrex',
                    'document_id': document.document_id,
                })
                continue
            logging.getLogger('statbox').info({
                'action': 'retrieve_content',
                'mode': 'cybrex',
                'document_id': document.document_id,
            })
            document_chunks = await self.generate_chunks_from_document(document)
            all_chunks.extend(document_chunks)
        return all_chunks

    async def upsert_documents(self, documents: List[SourceDocument], skip_downloading_pdf: bool = True):
        """
        Upsert documents into vector storage

        :param documents:
        :param skip_downloading_pdf:
        :return:
        """

        # ToDo: need concurrent upserts. For these purposes we may use critical
        #  locked area on inserting using primary keys

        if not documents:
            return
        chunks = await self._get_missing_chunks(documents, skip_downloading_pdf=skip_downloading_pdf)
        if chunks:
            logging.getLogger('statbox').info({
                'action': 'add_full_documents',
                'mode': 'cybrex',
                'n': len(chunks),
            })
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.vector_storage.upsert(chunks)
            )
            logging.getLogger('statbox').info({
                'action': 'added_full_documents',
                'mode': 'cybrex',
                'n': len(chunks),
            })

    async def upsert_document_by_query(self, query: str, skip_downloading_pdf: bool = True):
        """
        Query documents from data source and upsert them into vector storage

        :param query:
        :param skip_downloading_pdf:
        :return:
        """
        documents = await self.data_source.query_documents(query, limit=1)
        if not documents:
            raise DocumentNotFoundError(id_=query)
        await self.upsert_documents(documents, skip_downloading_pdf=skip_downloading_pdf)
        return documents[0].document_id

    async def export_chunks(self, query: str, output_path: str, n_documents: int, skip_downloading_pdf: bool = True):
        documents = await self.search(query, n_documents=n_documents)
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
        """
        Import binary file with embeddings

        :param input_path:
        """

        chunks = []
        with GzipFile(input_path, mode='rb') as zipper:
            for line in zipper.readlines():
                chunk = json.loads(line)
                if 'metadata' in chunk:
                    if 'id' in chunk['metadata']:
                        chunk['document_id'] = chunk['metadata'].pop('id')
                    if 'doi' in chunk['metadata']:
                        chunk['document_id'] = f'nexus_science:doi:{chunk["metadata"].pop("doi")}'
                    chunk.update(chunk.pop('metadata'))
                chunks_from_storage = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: self.vector_storage.get_by_field_value('document_id', chunk['document_id'])
                )
                if chunks_from_storage:
                    logging.getLogger('statbox').info({
                        'action': 'already_stored',
                        'mode': 'cybrex',
                        'document_id': chunk['document_id'],
                    })
                    continue
                chunk['embedding'] = base64.b64decode(chunk['embedding'])
                chunk['embedding'] = [n.item() for n in np.frombuffer(chunk['embedding'], dtype=np.float64)]
                chunks.append(chunk)

        if chunks:
            await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.vector_storage.upsert(chunks),
            )

    async def _query(self, query: str, n_chunks: int = 3, where: Optional[dict] = None, minimum_score: float = 0.5):
        logging.getLogger('statbox').info({
            'action': 'query',
            'mode': 'cybrex',
            'query': query,
            'n_chunks': n_chunks,
            'where': where,
        })
        chunks = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: self.vector_storage.query(self.model.embedder.embed_query(query), n_chunks=n_chunks, where=where),
        )
        filtered_chunks = []
        for chunk in chunks:
            if chunk['score'] > minimum_score:
                filtered_chunks.append(chunk)
        logging.getLogger('statbox').info({
            'action': 'query',
            'mode': 'cybrex',
            'found': len(filtered_chunks),
            'minimum_score': minimum_score,
        })
        return filtered_chunks

    async def search(self, query: str, n_documents: int):
        if not n_documents:
            return []

        if self.model.keyword_extractor:
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

            keywords = list(map(lambda x: x[1][0], filter(lambda x: x[1][1] > 0.5 or x[0] < 2, enumerate(keywords))))
            query = ' '.join(keywords)

        logging.getLogger('statbox').info({
            'action': 'query',
            'mode': 'cybrex',
            'query': query,
        })
        documents = await self.data_source.query_documents(query=query, limit=n_documents)
        return documents

    async def semantic_search(self, query: str, n_chunks: int = 10, n_documents: int = 30, minimum_score: float = 0.5):
        documents = await self.search(query, n_documents)
        await self.upsert_documents(documents)
        chunks = await self._query(query, n_chunks, minimum_score=minimum_score)
        return chunks

    async def chat_document(self, document_query: str, query: str, n_chunks: int, minimum_score: float = 0.5):
        document_id = await self.upsert_document_by_query(str(document_query), skip_downloading_pdf=False)
        chunks = await self._query(
            query=query,
            n_chunks=n_chunks,
            where={'document_id': document_id},
            minimum_score=minimum_score,
        )

        chain = QAChain(query=query, llm_manager=self.model.llm_manager)
        answer = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: chain.process(chunks),
        )

        return answer.strip(), chunks

    async def chat_science(self, query: str, n_chunks: int, n_documents: int, minimum_score: float = 0.5):
        if n_chunks:
            chunks = await self.semantic_search(
                query=query,
                n_chunks=n_chunks,
                n_documents=n_documents,
                minimum_score=minimum_score,
            )
            chain = QAChain(query=query, llm_manager=self.model.llm_manager)
            answer = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: chain.process(chunks),
            )
            return answer.strip(), chunks
        else:
            answer = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.model.llm_manager.process(self.model.llm_manager.prompter.question(query)),
            )
            return answer.strip(), []

    async def summarize_document(self, document_query):
        document_id = await self.upsert_document_by_query(document_query, skip_downloading_pdf=False)
        chunks = self.vector_storage.get_by_field_value('document_id', document_id)
        chain = SummarizeChain(llm_manager=self.model.llm_manager)
        answer = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: chain.process(chunks),
        )
        return answer.strip(), chunks

    async def general_text_processing(self, request, text):
        """
        Process user's request using text

        :param request:
        :param text:
        :return:
        """
        answer = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: self.model.llm_manager.process(
                self.model.llm_manager.prompter.general_text_processing(request=request, text=text)
            ),
        )
        return answer.strip()

    async def get_documents_from_chunks(self, chunks):
        """
        Return original documents using GECK and identifiers from chunks

        :param chunks:
        :return:
        """
        ids = set([chunk['document_id'] for chunk in chunks])
        subqueries = []
        for id_ in ids:
            field, value = id_.split(':', 1)
            subqueries.append({'query': {'match': {'value': f'{field}:"{value}"'}}, 'occur': 'should'})

        search_request = {
            'index_alias': 'nexus_science',
            'query': {'boolean': {'subqueries': subqueries}},
            'collectors': [{'top_docs': {'limit': len(subqueries)}}],
            'is_fieldnorms_scoring_enabled': False,
        }
        return await self.geck.get_summa_client().search_documents(search_request)
