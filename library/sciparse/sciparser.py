import asyncio
import hashlib
import logging
import os.path
import random

from aiocrossref import CrossrefClient
from aiokit import AioThing
from bs4 import (
    BeautifulSoup,
    NavigableString,
)
from stc_geck.advices import BaseDocumentHolder

from library.pdftools import is_pdf

SECTIONS_MAPS = {
    "Authors": "Authors",
    "AUTHORS": "Authors",
    "Abstract": "Abstract",
    "ABSTRACT": "Abstract",
    "Date": "Date",
    "DATE": "Date",
    'acknowledgements': 'Acknowledgements',
    "INTRODUCTION": "Introduction",
    "MATERIALS AND METHODS": "Methods",
    "Materials and methods": "Methods",
    "METHODS": "Methods",
    "RESULTS": "Results",
    "CONCLUSIONS": "Conclusions",
    "CONCLUSIONS AND FUTURE APPLICATIONS": "Conclusions",
    "DISCUSSION": "Discussion",
    "ACKNOWLEDGMENTS": "Acknowledgements",
    "TABLES": "Tables",
    "Tabnles": "Tables",
    "DISCLOSURE": "Disclosure",
    "CONFLICT OF INTEREST": "Disclosure",
    "Declaration of conflicting interests": "Disclosure",
    'Declaration of competing interest': "Disclosure",
    "Acknowledgement": "Acknowledgements",
    'Acknowledgments': 'Acknowledgements',
    'conflictofintereststatement': 'Disclosure',
    "FUNDING": 'Funding',
    'fundinginformation': 'Funding',
    "BIOGRAPHIES": "Biographies",
    'disclaimer': 'Disclosure',
    'referencesfigure': 'References Figure',
    'declaration of competing interest': 'Disclosure',
    'conflict of interest disclosures': 'Disclosure',
    'conflict of interest statement': 'Disclosure',
}


class LeasedItem:
    def __init__(self, pool: 'ClientPool'):
        self.pool = pool
        self.client = None

    async def __aenter__(self):
        self.client = await self.pool.free_queue.get()
        logging.getLogger('statbox').info({'action': 'lease', 'mode': 'sciparser_pool', 'base_url': self.client.base_url})
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.pool.free_queue.put(self.client)


class ClientPool(AioThing):
    def __init__(self, clients_and_weights):
        super().__init__()
        self.free_queue = asyncio.Queue()
        clients = []
        for client, weight in clients_and_weights:
            clients.extend([client] * weight)
        random.shuffle(clients)
        for client in clients:
            self.free_queue.put_nowait(client)

    @staticmethod
    def from_client(client, par):
        return ClientPool((client, par))

    @staticmethod
    def from_pool_config(cls, pool_config):
        clients_and_weights = []
        clients = []
        for client_config in pool_config:
            client = cls(**client_config['config'])
            clients_and_weights.append((client, client_config['weight']))
            clients.append(client)
        client_pool = ClientPool(clients_and_weights)
        client_pool.starts.extend(clients)
        return client_pool

    def lease(self) -> LeasedItem:
        return LeasedItem(self)


class SciParser(AioThing):
    def __init__(self, ipfs_http_client, grobid_pool):
        super().__init__()
        self.ipfs_http_client = ipfs_http_client
        self.grobid_pool = grobid_pool
        self.crossref_client = CrossrefClient()
        self.starts.append(self.crossref_client)

    async def process_document_in_grobid(self, data):
        async with self.grobid_pool.lease() as grobid_client:
            grobid_response = await grobid_client.post(
                '/api/processFulltextDocument',
                data={
                    'input': data,
                },
            )
        parsed_response = BeautifulSoup(grobid_response, features="lxml")
        return parsed_response

    async def parse_paper(self, document):
        if 'data' in document:
            data = document['data']
        else:
            document_holder = BaseDocumentHolder(document)
            pdf_link = document_holder.get_links().get_link_with_extension('pdf')
            if not pdf_link:
                return
            data = await self.ipfs_http_client.get_item(pdf_link["cid"])
            pdf_link['filesize'] = len(data)
            if 'md5' not in pdf_link:
                pdf_link['md5'] = await asyncio.get_running_loop().run_in_executor(None, lambda: hashlib.md5(data).hexdigest())
        if not is_pdf(data) and 'doi' in document:
            with open(os.path.expanduser('~/not_pdf.txt'), 'a') as f:
                f.write(document['doi'] + '\n')
        article = await self.process_document_in_grobid(data)

        article_dict = {}
        if article is not None:
            if title := article.find("title", attrs={"type": "main"}):
                if title := title.text.strip():
                    article_dict["title"] = title
            if issued_at := self.parse_date(article):
                article_dict["issued_at"] = issued_at

            if 'abstract' not in document or len(document['abstract']) < 16:
                article_dict["abstract"] = self.parse_abstract(article)

            if content := self.parse_content(article.find("text")):
                article_dict["content"] = content

            if keywords := self.parse_keywords(article):
                article_dict["keywords"] = keywords

            doi = article.find("idno", attrs={"type": "DOI"})
            doi = doi.text.lower() if doi is not None else None
            if doi:
                article_dict["doi"] = doi.lower()
            return article_dict
        else:
            return

    def parse_date(self, article):
        """
        Parse date from a given BeautifulSoup of an article
        """
        pub_date = article.find("publicationstmt")
        year = pub_date.find("date")
        year = year.attrs.get("when") if year is not None else ""
        return year

    def parse_abstract(self, article):
        """
        Parse abstract from a given BeautifulSoup of an article
        """
        divs = article.find("abstract").find_all("div", attrs={"xmlns": "http://www.tei-c.org/ns/1.0"})
        sections = []
        for div in divs:
            div_list = list(div.children)
            if len(div_list) == 0:
                heading = ""
                text = ""
            elif len(div_list) == 1:
                heading = ""
                text = str(div_list[0])
            else:
                text = []
                heading = div_list[0]
                if isinstance(heading, NavigableString):
                    heading = str(heading)
                    p_all = list(div.children)[1:]
                else:
                    heading = ""
                    p_all = list(div.children)
                for p in p_all:
                    if p is not None:
                        try:
                            text.append(str(p))
                        except:
                            pass
                text = "\n".join(text)

            section_parts = []
            if heading:
                mapped_heading = SECTIONS_MAPS.get(heading)
                if not mapped_heading:
                    mapped_heading = SECTIONS_MAPS.get(''.join(heading.lower()), heading)
                if mapped_heading:
                    section_parts.append(f'<header>{mapped_heading}</header>')
            if text:
                section_parts.append(text)
            if section_parts:
                section_text = ''.join(section_parts).strip()
                if section_text:
                    sections.append('<section>' + section_text + '</section>')
        abstract = '\n'.join(sections).removeprefix('Abstract\n').strip()
        return '<abstract>' + abstract + "</abstract>"

    def parse_keywords(self, article):
        """
        Parse abstract from a given BeautifulSoup of an article
        """
        div = article.find("keywords")
        keywords = []
        if keywords:
            for term in div.find_all("term"):
                keywords.append(term.text.strip().lower())
        return keywords

    def parse_content(self, article):
        """
        Parse list of sections from a given BeautifulSoup of an article
        """
        divs = article.find_all("div", attrs={"xmlns": "http://www.tei-c.org/ns/1.0"})
        sections = []
        for div in divs:
            div_list = list(div.children)
            if len(div_list) == 0:
                heading = ""
                text = ""
            elif len(div_list) == 1:
                if isinstance(div_list[0], NavigableString):
                    heading = str(div_list[0])
                    text = ""
                else:
                    heading = ""
                    text = str(div_list[0])
            else:
                text = []
                heading = div_list[0]
                if isinstance(heading, NavigableString):
                    heading = str(heading)
                    p_all = list(div.children)[1:]
                else:
                    heading = ""
                    p_all = list(div.children)
                for p in p_all:
                    if p is not None:
                        try:
                            text.append(str(p))
                        except:
                            pass
                text = "\n".join(text)

            section_parts = []
            if heading:
                mapped_heading = SECTIONS_MAPS.get(heading)
                if not mapped_heading:
                    mapped_heading = SECTIONS_MAPS.get(''.join(heading.lower()), heading)
                if mapped_heading:
                    section_parts.append(f'<header>{mapped_heading}</header>')
            if text:
                section_parts.append(text)

            if section_parts:
                sections.append('<section>' + '\n'.join(section_parts) + '</section>')
        return '<content>' + ''.join(sections) + '</content>'

    def parse_references(self, article):
        """
        Parse list of references from a given BeautifulSoup of an article
        """
        references = article.find("text").find("div", attrs={"type": "references"})
        references = references.find_all("biblstruct") if references is not None else []
        reference_list = []
        for reference in references:
            title = reference.find("title", attrs={"level": "a"})
            if title is None:
                title = reference.find("title", attrs={"level": "m"})
            title = title.text if title is not None else ""
            journal = reference.find("title", attrs={"level": "j"})
            journal = journal.text if journal is not None else ""
            if journal == "":
                journal = reference.find("publisher")
                journal = journal.text if journal is not None else ""
            year = reference.find("date")
            year = year.attrs.get("when") if year is not None else ""
            authors = []
            for author in reference.find_all("author"):
                firstname = author.find("forename", {"type": "first"})
                firstname = firstname.text.strip() if firstname is not None else ""
                middlename = author.find("forename", {"type": "middle"})
                middlename = middlename.text.strip() if middlename is not None else ""
                lastname = author.find("surname")
                lastname = lastname.text.strip() if lastname is not None else ""
                if middlename != "":
                    authors.append(firstname + " " + middlename + " " + lastname)
                else:
                    authors.append(firstname + " " + lastname)
            authors = "; ".join(authors)
            reference_list.append(
                {"title": title, "journal": journal, "year": year, "authors": authors}
            )
        return reference_list