import asyncio
import json
import tempfile

from langchain.chains import RetrievalQA
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from stc_tools.client import StcTools


def print_color(text, color):
    print("\033[38;5;{}m{}\033[0m".format(color, text))

async def request_documents(stc_tools, topic: str):
    SHOULD = 0
    MUST = 1
    MUST_NOT = 2

    search_results = await stc_tools.search([{
        "index_alias": "nexus_science",
        "query": {"query": {"boolean": {"subqueries": [
            {"occur": SHOULD, "query": {"query": {"match": {"value": topic, "default_fields": ["title", "abstract"], "field_boosts": {}}}}},
        ]}}},
        "collectors": [{"collector": {"top_docs": {"limit": 20, "scorer": {"scorer": {
            "eval_expr": "original_score * fastsigm(abs(now - issued_at) / (86400 * 3) + 5, -1) * 1.96 * fastsigm(iqpr(quantized_page_rank), 0.15)",
        }}}}}],
        "is_fieldnorms_scoring_enabled": False,
    }])
    documents = search_results[0]['collector_output']['documents']['scored_documents']
    texts = []
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=300)
    downloaded_dois = []

    if documents:
        for document in documents:
            document_meta = json.loads(document['document'])
            if 'content' in document_meta:
                downloaded_dois.append(document_meta['doi'])
                with tempfile.NamedTemporaryFile('w') as f:
                    f.write(document_meta['abstract'] + '\n' + document_meta['content'])
                    f.flush()
                    loader = TextLoader(f.name)
                    processed_document = loader.load_and_split()
                    texts.extend(text_splitter.split_documents(processed_document))
            elif 'cid' in document_meta:
                downloaded_dois.append(document_meta['doi'])
                pdf_file = await stc_tools.download(document_meta['cid'])
                with tempfile.NamedTemporaryFile('wb') as f:
                    f.write(pdf_file)
                    f.flush()
                    loader = PyPDFLoader(f.name)
                    processed_document = loader.load_and_split()
                    texts.extend(text_splitter.split_documents(processed_document))
            else:
                continue
        if not texts:
            raise RuntimeError("Change topic, unfortunately no appropriate documents have been found in STC")
        print_color("Used DOIs: " + ', '.join(downloaded_dois), 46)
        return texts
    else:
        raise RuntimeError('Paper has been not found!')


async def main():
    stc_tools = StcTools()
    await stc_tools.setup()

    topic = input("Input topic: ")
    texts = await request_documents(stc_tools, topic)

    embeddings = OpenAIEmbeddings()
    db = Chroma.from_documents(texts, embeddings, persist_directory="docs.db")
    retriever = db.as_retriever()
    qa = RetrievalQA.from_chain_type(llm=OpenAI(), chain_type="stuff", retriever=retriever)
    while True:
        question = input("Question: ")
        result = qa({"query": question})
        print_color("Answer: " + result["result"], 46)


if __name__ == '__main__':
    asyncio.run(main())