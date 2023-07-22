from ctransformers.langchain import CTransformers
from keybert import KeyBERT
from langchain import (
    OpenAI,
    PromptTemplate,
)
from langchain.chains import RetrievalQA
from langchain.embeddings import (
    HuggingFaceInstructEmbeddings,
    OpenAIEmbeddings,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from lazy import lazy

wizardlm_question_prompt = """
A chat between a curious user and an artificial intelligence assistant.
If assistant doesn't know the answer, it says that he doesn't know and doesn't try to make up an answer.
Assistant can use the following pieces of context to answer the question.

{context}

USER: {question}
ASSISTANT: """

wizardlm_combine_prompt = """
A chat between a curious user and an artificial intelligence assistant.
If assistant doesn't know the answer, it says that he doesn't know and doesn't try to make up an answer.
The assistant gives helpful, detailed, and polite answers to the user's questions.
Use the following extracted parts of a long document and a question at the end, create a final answer. 

{summaries}

USER: {question}
ASSISTANT: """


class BaseModel:
    @lazy
    def keyword_extractor(self):
        return KeyBERT()


class DefaultModel(BaseModel):
    name = 'wizardlm-13b-uncensored_instructor-xl_rcts-2048-256'

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=2048, chunk_overlap=256)

    @lazy
    def llm(self):
        return CTransformers(
            model='TheBloke/WizardLM-13B-uncensored-GGML',
            model_file='wizardLM-13B-Uncensored.ggmlv3.q5_1.bin',
            model_type='llama',
        )

    @lazy
    def embedding_function(self):
        return HuggingFaceInstructEmbeddings(
            model_name='hkunlp/instructor-xl',
            embed_instruction="Represent science paragraph for retrieval",
            query_instruction="Represent science question for retrieval",
        )

    def get_retrieval_qa(self, retriever):
        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type='stuff',
            chain_type_kwargs={
                "question_prompt": PromptTemplate(
                    template=wizardlm_question_prompt,
                    input_variables=["context", "question"],
                ),
                "combine_prompt": PromptTemplate(
                    template=wizardlm_combine_prompt,
                    input_variables=["summaries", "question"],
                ),
            },
            retriever=retriever,
            return_source_documents=True,
        )


class OpenAIModel(BaseModel):
    name = 'open-ai_open-ai_rcts-2048-256'

    def __init__(self):
        self.llm = OpenAI()
        self.embedding_function = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=2048, chunk_overlap=256)

    def get_retrieval_qa(self, retriever):
        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type='map_reduce',
            retriever=retriever,
            return_source_documents=True,
        )


models_dict = {
    DefaultModel.name: DefaultModel,
    OpenAIModel.name: OpenAIModel,
}
