import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import (
    List,
    Optional,
)

import unstructured.documents.elements
from bs4 import BeautifulSoup
from unstructured.chunking.title import (
    _split_elements_by_title_and_table,
    chunk_table_element,
)
from unstructured.cleaners.core import clean
from unstructured.partition.html import partition_html

from .data_source.base import SourceDocument

BANNED_SECTIONS = {
    'author contribution',
    'data availability statement',
    'declaration of competing interest',
    'acknowledgments',
    'acknowledgements',
    'supporting information',
    'conflict of interest disclosures',
    'conflict of interest statement',
    'ethics statement',
}


@dataclass
class Chunk:
    document_id: Optional[str]
    chunk_id: Optional[int]
    title: Optional[str]
    length: Optional[int]
    # What should be stored in the database
    text: Optional[str] = None
    # What should be embedded, defaults to `text` if None
    real_text: Optional[str] = None
    embedding: Optional[bytes] = None
    with_content: bool = False


def chunk_by_title(
    elements: List[unstructured.documents.elements.Element],
    multipage_sections: bool = True,
) -> List[unstructured.documents.elements.Element]:
    chunked_elements: List[unstructured.documents.elements.Element] = []
    sections = _split_elements_by_title_and_table(
        elements,
        multipage_sections=multipage_sections,
        combine_text_under_n_chars=0,
        new_after_n_chars=2 ** 31,
    )
    last_title_parts = -1
    current_title_parts = [''] * 6

    for section in sections:
        if not section:
            continue

        first_element = section[0]

        if isinstance(first_element, unstructured.documents.elements.Title):
            current_title_parts[first_element.metadata.category_depth] = re.sub('\n+', ' ', str(first_element))
            last_title_parts = first_element.metadata.category_depth
            continue

        if not isinstance(first_element, unstructured.documents.elements.Text):
            chunked_elements.extend(section)
            continue

        elif isinstance(first_element, unstructured.documents.elements.Table):
            chunked_elements.extend(chunk_table_element(first_element, max_characters=2 ** 63))
            continue

        text = ""
        metadata = first_element.metadata
        if last_title_parts != -1:
            metadata.section = '\n'.join(current_title_parts[:last_title_parts + 1])
        start_char = 0
        for i, element in enumerate(section):
            if isinstance(element, unstructured.documents.elements.Text):
                text += "\n\n" if text else ""
                start_char = len(text)
                text += element.text
            for attr, value in vars(element.metadata).items():
                if isinstance(value, list):
                    _value = getattr(metadata, attr, []) or []

                    if attr == "regex_metadata":
                        for item in value:
                            item["start"] += start_char
                            item["end"] += start_char

                    _value.extend(item for item in value if item not in _value)
                    setattr(metadata, attr, _value)

        chunked_elements.append(unstructured.documents.elements.CompositeElement(text=text, metadata=metadata))

    return chunked_elements


class DocumentChunker:
    def __init__(self, text_splitter, minimal_chunk_size: int = 128, add_metadata: bool = False):
        self.text_splitter = text_splitter
        self.minimal_chunk_size = minimal_chunk_size
        self.add_metadata = add_metadata

    def to_chunks(self, source_document: SourceDocument) -> List[Chunk]:
        logging.getLogger('statbox').info({
            'action': 'chunking',
            'document_id': source_document.document_id,
            'mode': 'cybrex',
        })
        document = source_document.document
        abstract = document.get('abstract', '')
        content = document.get('content', '')

        soup = BeautifulSoup('<html>' + abstract + content + '</html>', 'lxml')

        for section in list(soup.find_all('section')):
            for child in section.children:
                if (
                    child.name in {'header', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
                    and child.text.lower().strip() in BANNED_SECTIONS
                ):
                    section.extract()
                break

        for header in list(soup.find_all('header')):
            header.name = 'h1'

        for el in list(soup.select('nav, ref, formula, math, figure, .Affiliations, '
                                   '.ArticleOrChapterToc, '
                                   '.AuthorGroup, .ChapterContextInformation, '
                                   '.Contacts, .CoverFigure, .Bibliography, '
                                   '.BookTitlePage, .BookFrontmatter, .CopyrightPage, .Equation, '
                                   '.FootnoteSection, .Table')):
            el.extract()

        for el in list(soup.select('a')):
            el.unwrap()

        text = str(soup)
        text = re.sub(r'\((?:[Ff]ig|[Tt]able|[Ss]ection)\.?\s*[^)]*\)', '', text)
        text = re.sub(r'\[[,\s–\d]*]', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s+([.,;])', '\g<1>', text, flags=re.MULTILINE)

        pre_elements = partition_html(text=text)
        elements = []
        for pre_element in pre_elements:
            if isinstance(pre_element, unstructured.documents.elements.Text):
                elements.append(pre_element)

        chunks = []
        chunk_id = 0

        elements = chunk_by_title(elements)
        for element in elements:
            for chunk in self.text_splitter.split_text(str(element)):
                chunk_text = clean(str(chunk), extra_whitespace=True, dashes=True, bullets=True, trailing_punctuation=True)
                if len(chunk_text) < self.minimal_chunk_size:
                    continue
                parts = [chunk_text]
                title_parts = [document["title"]]
                if self.add_metadata:
                    if element.metadata.section:
                        title_parts.extend(element.metadata.section.split('\n'))
                    parts.append(f'TITLE: {" ".join(title_parts)}')
                    if 'issued_at' in document:
                        issued_at = datetime.utcfromtimestamp(document['issued_at'])
                        parts.append(f'YEAR: {issued_at.year}')
                    if 'metadata' in document and 'keywords' in document['metadata']:
                        keywords = ', '.join(document['metadata']['keywords'])
                        parts.append(f'KEYWORDS: {keywords}')
                    if 'tags' in document:
                        tags = ', '.join(document['tags'])
                        parts.append(f'TAGS: {tags}')
                text = '\n'.join(parts)
                chunks.append(Chunk(
                    real_text=text,
                    text=chunk_text,
                    document_id=source_document.document_id,
                    length=len(text),
                    chunk_id=chunk_id,
                    title='\n'.join(title_parts),
                    with_content=bool(content),
                ))
                chunk_id += 1
        return chunks
