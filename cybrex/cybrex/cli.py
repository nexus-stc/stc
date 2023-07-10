import logging
import sys
import textwrap

import fire
from termcolor import colored

from .cybrex_ai import CybrexAI


def create_snippet(document):
    return document.metadata['doi'] + ': ' + document.page_content


class CybrexCli:
    def __init__(self):
        self.cybrex = CybrexAI()

    async def chat_doc(self, field: str, value: str, question: str, k: int = 7):
        """
        Ask a question about content of document identified by DOI.

        :param field: name of the field in document used for selection
        :param value: value of the field in document used for selection
        :param question: Text question to the document
        :param k: the number of documents to extract from Chroma for sending to OpenAI
            more means more tokens to use and more precision in answer
        """
        async with self.cybrex as cybrex:
            print(f"{colored('Document', 'green')}: {field}:{value}")
            print(f"{colored('Q', 'green')}: {question}")
            response = await cybrex.chat_document(field, value, question, k)
            print(f"{colored('A', 'green')}: {response}")

    async def chat_sci(self, topic: str, question: str, llm_documents: int = 11, summa_documents: int = 40):
        """
        Ask a question about content of document identified by DOI.

        :param topic:
        :param question: Text question to the document
        :param llm_documents: the number of documents to extract from Chroma for sending to OpenAI
            more means more tokens to use and more precision in answer
        :param summa_documents: the number of documents to extract from Chroma for sending to OpenAI
            more means more tokens to use and more precision in answer
        """
        async with self.cybrex as cybrex:
            print(f"{colored('Topic', 'green')}: {topic}")
            print(f"{colored('Q', 'green')}: {question}")
            response = await cybrex.chat_science(
                topic=topic,
                question=question,
                llm_documents=llm_documents,
                summa_documents=summa_documents,
            )
            print(f"{colored('A', 'green')}: {response['result'].strip()}")
            snippets = [create_snippet(source_document) for source_document in response['source_documents']]
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


async def cybrex_cli(debug: bool = False):
    """
    :param debug: add debugging output
    :return:
    """
    logging.basicConfig(stream=sys.stdout, level=logging.INFO if debug else logging.ERROR)
    cybrex_ai = CybrexCli()
    return {
        'chat-doc': cybrex_ai.chat_doc,
        'chat-sci': cybrex_ai.chat_sci,
        'sum-doc': cybrex_ai.sum_doc,
    }


def main():
    fire.Fire(cybrex_cli, name='cybrex')


if __name__ == '__main__':
    main()
