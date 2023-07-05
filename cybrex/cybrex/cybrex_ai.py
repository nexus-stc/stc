import os.path
import uuid
from typing import List, Optional

import chromadb
import pypdf
import yaml
from aiokit import AioThing
from izihawa_configurator import Configurator
from izihawa_utils.exceptions import BaseError
from izihawa_utils.file import mkdir_p
from langchain.chains import RetrievalQA
from langchain.chains.summarize import load_summarize_chain
from langchain.embeddings import OpenAIEmbeddings
from langchain.embeddings.base import Embeddings
from langchain.llms import OpenAI
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from stc_geck.advices import get_documents_on_topic
from stc_geck.client import StcGeck


class DocumentNotFoundError(BaseError):
    pass


def print_color(text, color):
    print("\033[38;5;{}m{}\033[0m".format(color, text))


def default_config():
    return {
        'summa': {
            'endpoint': '127.0.0.1:10083'
        },
        'ipfs': {
            'http': {
                'base_url': 'http://127.0.0.1:8080'
            }
        }
    }


class CybrexAI(AioThing):
    def __init__(
        self,
        home_path: str = '~/.cybrex',
        collection_name: str = 'main',
        embedding_function: Optional[Embeddings] = None,
        geck: Optional[StcGeck] = None,
    ):
        super().__init__()
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

        self.client_settings = chromadb.config.Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=os.path.join(self.home_path, 'chroma'),
        )
        self.db = chromadb.Client(self.client_settings)
        self.collection_name = collection_name

        self.embedding_function = embedding_function
        if self.embedding_function is None:
            self.embedding_function = OpenAIEmbeddings()

        real_embedding_function = self.embedding_function.embed_documents if self.embedding_function is not None else None
        self.collection = self.db.get_or_create_collection(
            name=self.collection_name,
            embedding_function=real_embedding_function,
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
            pdf_file = await self.geck.download(document['links'][0]['cid'])
            pdf_reader = pypdf.PdfReader(pdf_file)
            return '\n'.join(page.extract_text() for page in pdf_reader.pages)

    async def add_documents(self, documents: List[dict]):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=300)

        metadatas = []
        texts = []

        for document in documents:
            content = await self.resolve_document_content(document)
            if not content:
                continue
            for chunk_id, chunk in enumerate(text_splitter.split_text(content)):
                metadatas.append({'doi': document['doi'], 'chunk_id': chunk_id})
                texts.append(chunk)

        return self.collection.upsert(
            documents=texts,
            metadatas=metadatas,
            ids=[str(uuid.uuid1()) for _ in range(len(texts))]
        )

    async def chat_document(self, doi, question):
        await self.add_document_by_doi(doi)
        qa = RetrievalQA.from_chain_type(llm=OpenAI(), chain_type='stuff', retriever=self.as_retriever(
            search_type='similarity',
            search_kwargs={'k': 3, 'filter': {'doi': doi}},
        ))
        result = qa({"query": question})
        return result["result"].strip()

    async def summarize_document(self, doi):
        documents = await self.add_document_by_doi(doi)
        chain = load_summarize_chain(llm=OpenAI(), chain_type="map_reduce")
        result = chain.run(documents)
        return result.strip()

    async def add_document_by_doi(self, doi) -> List[Document]:
        if not self.collection.get(where={'doi': doi}):
            documents = await self.geck.get_summa_client().search_documents([{
                'index_alias': 'nexus_science',
                'collectors': [{'top_docs': {'limit': 1}}],
                'query': {'term': {'field': 'doi', 'value': doi}}
            }])
            if not documents:
                raise DocumentNotFoundError(doi=doi)
            await self.add_documents(documents)
        return [Document(page_content=text) for text in self.collection.get(where={'doi': doi})['documents']]

    async def add_document_by_topic(self, topic):
        documents = await get_documents_on_topic(summa_client=self.geck.get_summa_client(), topic=topic, documents=20)
        return await self.add_documents(documents)

    def as_retriever(self, **kwargs):
        chroma = Chroma(
            client=self.db,
            collection_name=self.collection_name,
            persist_directory=self.home_path,
            embedding_function=self.embedding_function,
        )
        return chroma.as_retriever(**kwargs)
