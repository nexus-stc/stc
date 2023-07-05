import fire
from termcolor import colored

from .cybrex_ai import CybrexAI


class CybrexCli:
    def __init__(self):
        self.cybrex = CybrexAI()

    async def chat_doc(self, doi: str, question: str):
        """
        Ask a question about content of document identified by DOI.

        :param doi: DOI of the document
        :param question: Text question to the document
        """
        async with self.cybrex as cybrex:
            print(f"{colored('Document', 'green')}: {doi}")
            print(f"{colored('Q', 'green')}: {question}")
            response = await cybrex.chat_document(doi, question)
            print(f"{colored('A', 'green')}: {response}")

    async def sum_doc(self, doi: str,):
        """
        Summarization of the document

        :param doi: DOI of the document
        """
        async with self.cybrex as cybrex:
            print(f"{colored('Document', 'green')}: {doi}")
            response = await cybrex.summarize_document(doi)
            print(f"{colored('Summarization', 'green')}: {response}")


async def cybrex_cli():
    cybrex_ai = CybrexCli()
    return {
        'chat-doc': cybrex_ai.chat_doc,
        'sum-doc': cybrex_ai.sum_doc,
    }


def main():
    fire.Fire(cybrex_cli, name='cybrex')


if __name__ == '__main__':
    main()
