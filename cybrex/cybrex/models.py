import logging
from typing import List

from ctransformers import AutoModelForCausalLM
from keybert import KeyBERT
from langchain import OpenAI
from langchain.embeddings import (
    HuggingFaceInstructEmbeddings,
    OpenAIEmbeddings,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from lazy import lazy

from .prompts.base import BasePrompter


class LLM:
    def __init__(self, llm, prompter, config):
        self.llm = llm
        self.prompter = prompter
        self.config = config

    def process(self, prompt):
        logging.getLogger('statbox').info({'action': 'process', 'mode': 'llm', 'prompt': prompt})
        return self.llm(prompt)


def get_embedding_function(model_name):
    if model_name.startswith('hkunlp/instructor'):
        return HuggingFaceInstructEmbeddings(
            model_name=model_name,
            embed_instruction="Represent science paragraph for retrieval",
            query_instruction="Represent science question for retrieval",
        )
    elif model_name == "text-embedding-ada-002":
        return OpenAIEmbeddings(model=model_name)
    else:
        raise ValueError("Unsupported embedding model")


class CybrexModel:
    def __init__(self, config):
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config['text_splitter']['chunk_size'],
            chunk_overlap=self.config['text_splitter']['chunk_overlap'],
        )

    @classmethod
    def standard_llms(cls, name):
        return {
            'llama-2-7b': {
                'config': {
                    'context_length': 4096,
                    'max_new_tokens': 512,
                    'model_path_or_repo_id': 'TheBloke/Llama-2-7B-Chat-GGML',
                    'model_file': 'llama-2-7b-chat.ggmlv3.q4_K_S.bin',
                },
                'model_type': 'llama',
                'prompter': {
                    'type': 'llama-7b'
                }
            },
            'llama-2-7b-uncensored': {
                'config': {
                    'context_length': 4096,
                    'max_new_tokens': 512,
                    'model_path_or_repo_id': 'TheBloke/Luna-AI-Llama2-Uncensored-GGML',
                    'model_file': 'luna-ai-llama2-uncensored.ggmlv3.q4_K_S.bin',
                },
                'model_type': 'llama',
                'prompter': {
                    'type': 'default'
                },
            },
            'openai': {
                'config': {}
            },
        }[name]

    @classmethod
    def default_config(cls):
        return {
            'text_splitter': {
                'chunk_size': 1024,
                'chunk_overlap': 128,
                'type': 'rcts',
            },
            'embedder': {
                'model_name': 'hkunlp/instructor-xl',
                'model_type': 'instructor',
            },
            'llm': cls.standard_llms("llama-2-7b-uncensored")
        }

    @lazy
    def keyword_extractor(self):
        return KeyBERT()

    @lazy
    def embedder(self):
        if self.config['embedder']['model_type'] == 'instructor':
            return HuggingFaceInstructEmbeddings(
                model_name=self.config['embedder']['model_name'],
                embed_instruction="Represent science paragraph for retrieval",
                query_instruction="Represent science question for retrieval",
            )
        elif self.config['embedder']['model_type'] == 'openai':
            return OpenAIEmbeddings(model=self.config['embedder']['model_name'])
        else:
            raise ValueError("Unsupported embedding model")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embedder.embed_documents(texts)

    @lazy
    def llm(self):
        if self.config['llm']['model_type'] == 'llama':
            return LLM(
                llm=AutoModelForCausalLM.from_pretrained(**self.config['llm']['config']),
                prompter=BasePrompter.prompter_from_type(self.config['llm']['prompter']['type']),
                config=self.config['llm']['config'],
            )
        elif self.config['llm']['model_type'] == 'openai':
            return LLM(
                llm=OpenAI(**self.config['llm']['config']),
                prompter=BasePrompter.prompter_from_type(self.config['llm']['prompter']['type']),
                config=self.config['llm']['config'],
            )

    def get_embeddings_id(self):
        text_splitter_id = f'{self.config["text_splitter"]["type"]}' \
                           f'-{self.config["text_splitter"]["chunk_size"]}' \
                           f'-{self.config["text_splitter"]["chunk_overlap"]}'
        embedder_id = self.config['embedder']['model_name'].replace('/', '-')
        return f"{embedder_id}-{text_splitter_id}"
