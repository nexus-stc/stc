import logging
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup

from .data_source.base import SourceDocument


class DocumentChunker:
    def __init__(self, text_splitter, minimal_chunk_size: int = 128, add_metadata: bool = False):
        self.text_splitter = text_splitter
        self.minimal_chunk_size = minimal_chunk_size
        self.add_metadata = add_metadata

    def to_chunks(self, source_document: SourceDocument) -> List[dict]:
        logging.getLogger('statbox').info({
            'action': 'chunking',
            'document_id': source_document.document_id,
            'mode': 'cybrex',
        })
        document = source_document.document
        abstract = document.get('abstract', '')
        content = document.get('content')
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
            parts = []
            if self.add_metadata:
                if 'title' in document:
                    parts.append(f'TITLE: {document["title"]}')
                if 'issued_at' in document:
                    issued_at = datetime.utcfromtimestamp(document['issued_at'])
                    parts.append(f'YEAR: {issued_at.year}')
                if 'metadata' in document and 'keywords' in document['metadata']:
                    keywords = ', '.join(document['metadata']['keywords'])
                    parts.append(f'KEYWORDS: {keywords}')
                if 'tags' in document:
                    tags = ', '.join(document['tags'])
                    parts.append(f'TAGS: {tags}')
            parts.append(chunk)
            text = '\n'.join(parts)
            chunks.append({
                'real_text': text,
                'text': chunk,
                'document_id': source_document.document_id,
                'length': len(text),
                'chunk_id': chunk_id,
                'title': document["title"],
            })
        return chunks
