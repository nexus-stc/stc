import logging
from collections import OrderedDict
from typing import List

from ctransformers import AutoModelForCausalLM
from keybert import KeyBERT
from langchain import OpenAI
from langchain.embeddings import HuggingFaceInstructEmbeddings, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from lazy import lazy


class BasePrompter:
    @staticmethod
    def prompter_from_type(type_):
        return {
            'default': BasePrompter(),
            'llama2-7b': Llama27bPrompter(),
            'openai': OpenAIPrompter()
        }[type_]

    def qa_prompt(self, question, documents: List[dict]):
        if len(documents) > 1:
            return '''
USER: You are Cybrex AI created by People of Nexus. Given the following extracted parts of a long document and a question, create a final answer.
ALWAYS add references to extracted parts using template "DOI: 10.1038/s41576-022-00477-6" near corresponding statements. 
If you don't know the answer, just say that you don't know. Don't try to make up an answer.
Extracted parts:
{summary}

Question:
{question}
ASSISTANT:'''.format(question=question, summary=self.generate_summary(documents))
        else:
            return '''
USER: You are Cybrex AI created by People of Nexus. Given the following extracted parts of a long document and a question, create a final answer.
If you don't know the answer, just say that you don't know. Don't try to make up an answer.
Extracted parts:
{summary}

Question:
{question}
ASSISTANT:'''.format(question=question, summary=self.generate_summary(documents))

    def generate_summary(self, documents: List[dict]):
        document_summaries = []
        document_summaries_grouped = OrderedDict()
        for document in documents:
            if document["metadata"]["doi"] not in document_summaries_grouped:
                document_summaries_grouped[document["metadata"]["doi"]] = []
            document_summaries_grouped[document["metadata"]["doi"]].append(document['text'])
        for doi, texts in document_summaries_grouped.items():
            texts = ' <..> '.join(texts)
            document_summaries.append(f'DOI: {doi}\nCONTENT: {texts}')
        return '\n'.join(document_summaries)


class Llama27bPrompter(BasePrompter):
    def qa_prompt(self, question: str, documents: List[dict]):
        return '''
<s><<SYS>>
You are Cybrex AI created by People of Nexus. Given the following extracted parts of a long document and a question, create a final answer.
ALWAYS add references to extracted parts using template "DOI: 10.1038/s41576-022-00477-6" near corresponding statements. 
If you don't know the answer, just say that you don't know. Don't try to make up an answer.
<</SYS>>
[INST]
Extracted parts:
{summary}

Question:
{question}
[/INST]'''.format(question=question, summary=self.generate_summary(documents))


class OpenAIPrompter(BasePrompter):
    def qa_prompt(self, question: str, documents: List[dict]):
        return """Given the following extracted parts of a long document and a question, create a final answer with references ("DOIs"). 
If you don't know the answer, just say that you don't know. Don't try to make up an answer.
ALWAYS return a "DOIs" part in your answer.

QUESTION: Which state/country's law governs the interpretation of the contract?
=========
DOI: 28-pl
CONTENT: This Agreement is governed by English law and the parties submit to the exclusive jurisdiction of the English courts in  relation to any dispute (contractual or non-contractual) concerning this Agreement save that either party may apply to any court for an  injunction or other relief to protect its Intellectual Property Rights.
DOI: 30-pl
CONTENT: No Waiver. Failure or delay in exercising any right or remedy under this Agreement shall not constitute a waiver of such (or any other)  right or remedy.\n\n11.7 Severability. The invalidity, illegality or unenforceability of any term (or part of a term) of this Agreement shall not affect the continuation  in force of the remainder of the term (if any) and this Agreement.\n\n11.8 No Agency. Except as expressly stated otherwise, nothing in this Agreement shall create an agency, partnership or joint venture of any  kind between the parties.\n\n11.9 No Third-Party Beneficiaries.
DOI: 4-pl
CONTENT: (b) if Google believes, in good faith, that the Distributor has violated or caused Google to violate any Anti-Bribery Laws (as  defined in Clause 8.5) or that such a violation is reasonably likely to occur,
=========
FINAL ANSWER: This Agreement is governed by English law (DOI: 28-pl)

QUESTION: What did the president say about Michael Jackson?
=========
DOI: 0-pl
CONTENT: Madam Speaker, Madam Vice President, our First Lady and Second Gentleman. Members of Congress and the Cabinet. Justices of the Supreme Court. My fellow Americans.  \n\nLast year COVID-19 kept us apart. This year we are finally together again. \n\nTonight, we meet as Democrats Republicans and Independents. But most importantly as Americans. \n\nWith a duty to one another to the American people to the Constitution. \n\nAnd with an unwavering resolve that freedom will always triumph over tyranny. \n\nSix days ago, Russia’s Vladimir Putin sought to shake the foundations of the free world thinking he could make it bend to his menacing ways. But he badly miscalculated. \n\nHe thought he could roll into Ukraine and the world would roll over. Instead he met a wall of strength he never imagined. \n\nHe met the Ukrainian people. \n\nFrom President Zelenskyy to every Ukrainian, their fearlessness, their courage, their determination, inspires the world. \n\nGroups of citizens blocking tanks with their bodies. Everyone from students to retirees teachers turned soldiers defending their homeland.
DOI: 24-pl
CONTENT: And we won’t stop. \n\nWe have lost so much to COVID-19. Time with one another. And worst of all, so much loss of life. \n\nLet’s use this moment to reset. Let’s stop looking at COVID-19 as a partisan dividing line and see it for what it is: A God-awful disease.  \n\nLet’s stop seeing each other as enemies, and start seeing each other for who we really are: Fellow Americans.  \n\nWe can’t change how divided we’ve been. But we can change how we move forward—on COVID-19 and other issues we must face together. \n\nI recently visited the New York City Police Department days after the funerals of Officer Wilbert Mora and his partner, Officer Jason Rivera. \n\nThey were responding to a 9-1-1 call when a man shot and killed them with a stolen gun. \n\nOfficer Mora was 27 years old. \n\nOfficer Rivera was 22. \n\nBoth Dominican Americans who’d grown up on the same streets they later chose to patrol as police officers. \n\nI spoke with their families and told them that we are forever in debt for their sacrifice, and we will carry on their mission to restore the trust and safety every community deserves.
DOI: 5-pl
CONTENT: And a proud Ukrainian people, who have known 30 years  of independence, have repeatedly shown that they will not tolerate anyone who tries to take their country backwards.  \n\nTo all Americans, I will be honest with you, as I’ve always promised. A Russian dictator, invading a foreign country, has costs around the world. \n\nAnd I’m taking robust action to make sure the pain of our sanctions  is targeted at Russia’s economy. And I will use every tool at our disposal to protect American businesses and consumers. \n\nTonight, I can announce that the United States has worked with 30 other countries to release 60 Million barrels of oil from reserves around the world.  \n\nAmerica will lead that effort, releasing 30 Million barrels from our own Strategic Petroleum Reserve. And we stand ready to do more if necessary, unified with our allies.  \n\nThese steps will help blunt gas prices here at home. And I know the news about what’s happening can seem alarming. \n\nBut I want you to know that we are going to be okay.
DOI: 34-pl
CONTENT: More support for patients and families. \n\nTo get there, I call on Congress to fund ARPA-H, the Advanced Research Projects Agency for Health. \n\nIt’s based on DARPA—the Defense Department project that led to the Internet, GPS, and so much more.  \n\nARPA-H will have a singular purpose—to drive breakthroughs in cancer, Alzheimer’s, diabetes, and more. \n\nA unity agenda for the nation. \n\nWe can do this. \n\nMy fellow Americans—tonight , we have gathered in a sacred space—the citadel of our democracy. \n\nIn this Capitol, generation after generation, Americans have debated great questions amid great strife, and have done great things. \n\nWe have fought for freedom, expanded liberty, defeated totalitarianism and terror. \n\nAnd built the strongest, freest, and most prosperous nation the world has ever known. \n\nNow is the hour. \n\nOur moment of responsibility. \n\nOur test of resolve and conscience, of history itself. \n\nIt is in this moment that our character is formed. Our purpose is found. Our future is forged. \n\nWell I know this nation.
=========
FINAL ANSWER: The president did not mention Michael Jackson.
DOIs:

QUESTION: {question}
=========
{summary}
=========
FINAL ANSWER:""".format(question=question, summary=self.generate_summary(documents))

class LLM:
    def __init__(self, llm, prompter):
        self.llm = llm
        self.prompter = prompter

    def ask_documents(self, question, documents):
        prompt = self.prompter.qa_prompt(question, documents)
        logging.getLogger('statbox').info({'action': 'ask_documents', 'mode': 'llm', 'prompt': prompt})
        return self.llm(prompt).strip()


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

    @lazy
    def llm(self):
        if self.config['llm']['model_type'] == 'llama':
            return LLM(
                llm=AutoModelForCausalLM.from_pretrained(**self.config['llm']['config']),
                prompter=BasePrompter.prompter_from_type(self.config['llm']['prompter']['type'])
            )
        elif self.config['llm']['model_type'] == 'openai':
            return LLM(
                llm=OpenAI(**self.config['llm']['config']),
                prompter=BasePrompter.prompter_from_type(self.config['llm']['prompter']['type']),
            )

    def get_embeddings_id(self):
        text_splitter_id = f'{self.config["text_splitter"]["type"]}' \
                           f'-{self.config["text_splitter"]["chunk_size"]}' \
                           f'-{self.config["text_splitter"]["chunk_overlap"]}'
        embedder_id = self.config['embedder']['model_name'].replace('/', '-')
        return f"{embedder_id}-{text_splitter_id}"
