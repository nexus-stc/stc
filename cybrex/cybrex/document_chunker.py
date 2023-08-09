import logging
from typing import List

from bs4 import BeautifulSoup

from .data_source.base import SourceDocument


class DocumentChunker:
    def __init__(self, text_splitter, minimal_chunk_size: int = 128):
        self.text_splitter = text_splitter
        self.minimal_chunk_size = minimal_chunk_size

    def to_chunks(self, document: SourceDocument) -> List[dict]:
        logging.getLogger('statbox').info({
            'action': 'chunking',
            'id': document.document_id,
            'mode': 'cybrex',
        })
        abstract = document.document.get('abstract', '')
        content = document.document.get('content')
        if not content:
            return []

        abstract_soup = BeautifulSoup(abstract, features='lxml')
        content_soup = BeautifulSoup(content, features='lxml')

        extracted_texts = []
        for section_id, section in enumerate(list(abstract_soup.children) + list(content_soup.children)):
            for el in list(section.find_all()):
                if el.name in {'ref', 'formula', 'math', 'figure'}:
                    el.extract()
            text = section.get_text(' ', strip=True)
            if len(text) < self.minimal_chunk_size:
                continue
            extracted_texts.append(text)

        chunks = []

        for chunk_id, chunk in enumerate(self.text_splitter.split_text('\n\n'.join(extracted_texts))):
            if len(chunk) < self.minimal_chunk_size:
                continue
            chunks.append({
                'text': chunk,
                'metadata': {
                    'id': document.document_id,
                    'length': len(chunk),
                    'chunk_id': chunk_id,
                }
            })
        return chunks
