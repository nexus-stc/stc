import json
import logging
import sys
import textwrap

import fire
from termcolor import colored

from .cybrex_ai import CybrexAI


def create_snippet(document, metadata):
    return metadata['doi'] + ': ' + document


class CybrexCli:
    def __init__(self):
        self.cybrex = CybrexAI()

    async def semantic_search(self, question: str, top_n: int = 7, summa_documents: int = 9):
        """
        Ask a question about content of document identified by DOI.

        :param question: question to STC
        :param top_n: number of pieces to return
        :param summa_documents: the number of documents to extract from Chroma
            more means more tokens to use and more precision in answer
        """
        async with self.cybrex as cybrex:
            print(f"{colored('Q', 'green')}: {question}")
            response = await cybrex.semantic_search(
                question=question,
                top_n=top_n,
                summa_documents=summa_documents
            )
            print(response)
            snippets = [
                ' - ' + create_snippet(document, metadata)
                for (document, metadata) in zip(response['documents'][0], response['metadatas'][0])
            ]
            sources = '\n'.join(snippets)
            print(f"{colored('Sources', 'green')}:\n{sources}")

    async def chat_doc(self, field: str, value: str, question: str, top_n: int = 7):
        """
        Ask a question about content of document identified by DOI.

        :param field: name of the field in document used for selection
        :param value: value of the field in document used for selection
        :param question: Text question to the document
        :param top_n: the number of documents to extract from Chroma
            more means more tokens to use and more precision in answer
        """
        async with self.cybrex as cybrex:
            print(f"{colored('Document', 'green')}: {field}:{value}")
            print(f"{colored('Q', 'green')}: {question}")
            response = await cybrex.chat_document(field, value, question, top_n)
            print(f"{colored('A', 'green')}: {response}")

    async def chat_sci(self, question: str, top_n: int = 7, summa_documents: int = 9):
        """
        Ask a question about content of document identified by DOI.

        :param question: Text question to the document
        :param top_n: the number of documents to extract from Chroma
            more means more tokens to use and more precision in answer
        :param summa_documents: the number of documents to extract from Chroma
            more means more tokens to use and more precision in answer
        """
        async with self.cybrex as cybrex:
            print(f"{colored('Q', 'green')}: {question}")
            response = await cybrex.chat_science(
                question=question,
                top_n=top_n,
                summa_documents=summa_documents,
            )
            print(f"{colored('A', 'green')}: {response['result'].strip()}")
            snippets = [create_snippet(source_document.page_content, source_document.metadata) for source_document in response['source_documents']]
            sources = textwrap.indent('\n'.join(snippets), ' - ')
            print(f"{colored('Sources', 'green')}:\n{sources}")

    async def sum_doc(self, field: str, value: str):
        """
        Summarization of the document

        :param field: name of the field in document used for selection
        :param value: value of the field in document used for selection
        """
        async with self.cybrex as cybrex:
            print(f"{colored('Document', 'green')}: {field}:{value}")
            response = await cybrex.summarize_document(field, value)
            print(f"{colored('Summarization', 'green')}: {response}")

    async def add_all_documents(self):
        async with self.cybrex as cybrex:
            async for document in cybrex.geck.get_summa_client().documents('nexus_science'):
                document = json.loads(document)
                await self.cybrex.add_documents([document])


async def cybrex_cli(debug: bool = False):
    """
    :param debug: add debugging output
    :return:
    """
    logging.basicConfig(stream=sys.stdout, level=logging.INFO if debug else logging.ERROR)
    cybrex_ai = CybrexCli()
    return {
        'add-all-documents': cybrex_ai.add_all_documents,
        'chat-doc': cybrex_ai.chat_doc,
        'chat-sci': cybrex_ai.chat_sci,
        'semantic-search': cybrex_ai.semantic_search,
        'sum-doc': cybrex_ai.sum_doc,
    }


def main():
    fire.Fire(cybrex_cli, name='cybrex')


if __name__ == '__main__':
    main()
