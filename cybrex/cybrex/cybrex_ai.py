import copy
import io
import logging
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
from keybert import KeyBERT
from langchain.chains import RetrievalQA
from langchain.chains.summarize import load_summarize_chain
from langchain.embeddings import HuggingFaceInstructEmbeddings
from langchain.embeddings.base import Embeddings
from langchain.llms import CTransformers
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


class EditableHuggingFaceInstructEmbeddings(HuggingFaceInstructEmbeddings):
    def with_instruction(self, query_instruction):
        c = copy.copy(self)
        c.query_instruction = query_instruction


class CybrexAI(AioThing):
    def __init__(
        self,
        home_path: str = '~/.cybrex',
        collection_name: str = 'main',
        embedding_function: Optional[Embeddings] = None,
        geck: Optional[StcGeck] = None,
        llm: Optional[str] = None,
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

        self.keyword_extractor = KeyBERT()
        self.llm = llm
        if self.llm is None:
            self.llm = CTransformers(
                model='TheBloke/WizardLM-13B-uncensored-GGML',
                model_file='wizardLM-13B-Uncensored.ggmlv3.q5_1.bin',
                model_type='llama',
            )
        self.embedding_function = embedding_function
        if self.embedding_function is None:
            self.embedding_function = EditableHuggingFaceInstructEmbeddings(
                model_name='hkunlp/instructor-xl',
                query_instruction="Represent science document for retrieval",
            )

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
            primary_link = document['links'][0]
            file_content = await self.geck.download(document['links'][0]['cid'])
            match primary_link['type']:
                case 'pdf':
                    pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
                    return '\n'.join(page.extract_text() for page in pdf_reader.pages)
                case _:
                    raise RuntimeError("Unsupported extension")

    async def add_documents(self, documents: List[dict]):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=256)

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
            logging.getLogger('statbox').info({
                'action': 'retrieve_content',
                'doi': doi,
            })
            content = await self.resolve_document_content(document)
            if not content:
                continue
            logging.getLogger('statbox').info({
                'action': 'chunking',
                'doi': doi,
            })
            for chunk_id, chunk in enumerate(text_splitter.split_text(content)):
                metadatas.append({'doi': doi, 'chunk_id': chunk_id})
                texts.append(chunk)
        if texts:
            return self.collection.upsert(
                documents=texts,
                metadatas=metadatas,
                ids=[str(uuid.uuid1()) for _ in range(len(texts))]
            )

    async def chat_document(self, field, value, question, k):
        await self.add_document_by_field_value(field, value)
        if k > 3:
            chain_type = 'map_reduce'
        else:
            chain_type = 'stuff'
        qa = RetrievalQA.from_chain_type(llm=self.llm, chain_type=chain_type, retriever=self.as_retriever(
            query_instruction="Represent science statement for retrieval",
            search_type='similarity',
            search_kwargs={'k': k, 'filter': {field: value}},
        ))
        result = qa({"query": f'{question}'})
        return result["result"].strip()

    async def chat_science(self, question, llm_documents, summa_documents):
        await self.add_document_for_question(question, summa_documents)
        qa = RetrievalQA.from_chain_type(llm=self.llm, chain_type='map_reduce', retriever=self.as_retriever(
            query_instruction="Represent science statement for retrieval",
            search_type='similarity',
            search_kwargs={'k': llm_documents},
        ), return_source_documents=True)
        result = qa({"query": question})
        return result

    async def summarize_document(self, field, value):
        documents = await self.add_document_by_field_value(field, value)
        chain = load_summarize_chain(llm=self.llm, chain_type="map_reduce")
        result = chain.run(documents)
        return result.strip()

    async def add_document_by_field_value(self, field, value) -> List[Document]:
        documents = await self.geck.get_summa_client().search_documents([{
            'index_alias': 'nexus_science',
            'collectors': [{'top_docs': {'limit': 1}}],
            'query': {'term': {'field': field, 'value': value}}
        }])
        if not documents:
            raise DocumentNotFoundError(**{field: value})
        await self.add_documents(documents)
        documents = [Document(page_content=text) for text in self.collection.get(where={field: value})['documents']]
        return documents

    async def add_document_for_question(self, question: str, documents: int):
        keywords = self.keyword_extractor.extract_keywords(
            question,
            top_n=3,
            keyphrase_ngram_range=(1, 1),
            stop_words=['a', 'the', 'in', 'is', 'was', 'are', 'were', 'am', 'at', 'of', 'out', 'what', 'should', 'will', 'why', 'for', 'from', 'and', 'or']
        )
        topic = ' '.join(map(lambda x: x[0], keywords))
        documents = await get_documents_on_topic(
            summa_client=self.geck.get_summa_client(),
            topic=topic,
            documents=documents,
        )
        return await self.add_documents(documents)

    def as_retriever(self, embedding_function=None, **kwargs):
        chroma = Chroma(
            client=self.db,
            collection_name=self.collection_name,
            persist_directory=self.home_path,
            embedding_function=embedding_function or self.embedding_function,
        )
        return chroma.as_retriever(**kwargs)
