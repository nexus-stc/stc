from urllib.parse import quote

import orjson

from library.regexes.utils import cast_string_to_single_string, escape_format

from .common import TooLongQueryError, encode_query_to_deep_link, recode_base36_to_base64
from .nexus_books import NexusBooksButtonsBuilder, NexusBooksViewBuilder
from .nexus_science import NexusScienceButtonsBuilder, NexusScienceViewBuilder


class BaseHolder:
    views_registry = {
        'nexus_science': NexusScienceViewBuilder,
        'nexus_books': NexusBooksViewBuilder,
    }

    def __init__(self, document, snippets=None):
        self.document = document
        self.snippets = snippets

    def __getattr__(self, name):
        if name in self.document:
            return self.document[name]
        elif 'metadata' in self.document and name in self.document['metadata']:
            return self.document['metadata'][name]

    @classmethod
    def create(cls, scored_document, snippets=None):
        if scored_document.index_alias == 'nexus_books':
            return NexusBooksHolder(orjson.loads(scored_document.document), snippets)
        if scored_document.index_alias == 'nexus_science':
            return NexusScienceHolder(orjson.loads(scored_document.document), snippets)

    def get_purified_name(self):
        limit = 55
        filename = cast_string_to_single_string(
            self.view_builder().add_authors(et_al=False).add_title(bold=False).add_formatted_datetime(with_months_for_recent=False).build().lower()
        )

        chars = []
        size = 0
        hit_limit = False

        for c in filename:
            current_size = size + len(c.encode())
            if current_size > limit:
                hit_limit = True
                break
            chars.append(c)
            size = current_size

        filename = ''.join(chars)
        if hit_limit:
            glyph = filename.rfind('-')
            if glyph != -1:
                filename = filename[:glyph]

        if not filename:
            if self.doi:
                filename = quote(self.doi, safe='')
            else:
                filename = self.md5

        return filename

    def get_filename(self) -> str:
        return f'{self.get_purified_name()}.{self.get_extension()}'

    def get_extension(self) -> str:
        return 'pdf'

    def get_formatted_filesize(self) -> str:
        if self.filesize:
            filesize = max(1024, self.filesize)
            return '{:.1f}Mb'.format(float(filesize) / (1024 * 1024))
        else:
            return ''

    def get_formatted_filedata(self, show_format=True, show_language=True, show_filesize=False) -> str:
        parts = []
        if show_language:
            if self.language and self.language != 'en':
                parts.append(self.language.upper())
        if show_format:
            extension = self.get_extension().upper()
            if extension != 'PDF':
                parts.append(extension)
        if self.has_field('filesize') and show_filesize:
            parts.append(self.get_formatted_filesize())
        return ' | '.join(parts)

    def get_ipfs_gateway_link(self):
        ipfs_link = (
            f'https://ipfs.io/ipfs/{self.cid}?'
            f'filename={quote(self.get_filename())}'
        )
        return f'[IPFS.io]({ipfs_link})'

    def get_ipfs_link(self):
        ipfs_link = (
            f'ipfs://{self.cid}?'
            f'filename={quote(self.get_filename())}'
        )
        return f'[IPFS]({ipfs_link})'

    def get_doi_link(self):
        return f'[{self.doi}](https://doi.org/{quote(self.doi)})'

    def encode_link(self, bot_name, text, query):
        try:
            encoded_query = encode_query_to_deep_link(query, bot_name)
            if text:
                return f'[{text}]({encoded_query})'
            else:
                return encoded_query
        except TooLongQueryError:
            return text

    def get_deep_author_link(self, bot_name, author):
        query = f'authors:"{author}"'
        return self.encode_link(bot_name, author, query)

    def get_deep_tag_link(self, bot_name, tag):
        query = f'tags:"{tag}"'
        return self.encode_link(bot_name, tag, query)

    def generate_links(self):
        links = []
        if self.cid:
            links.append(self.get_ipfs_gateway_link())
        if self.doi:
            links.append(self.get_doi_link())
        return links

    def generate_tags_links(self, bot_name):
        if self.tags:
            links = [self.get_deep_tag_link(bot_name=bot_name, tag=escape_format(tag)) for tag in self.tags]
            return links
        return []

    def has_field(self, name):
        return name in self.document or name in self.document.get('metadata', {})


class NexusScienceHolder(BaseHolder):
    index_alias = 'nexus_science'

    def view_builder(self, user_language=None):
        return NexusScienceViewBuilder(document_holder=self, user_language=user_language)

    def buttons_builder(self, user_language, remote_request_link=None):
        return NexusScienceButtonsBuilder(document_holder=self, user_language=user_language, remote_request_link=remote_request_link)

    def get_download_command(self) -> bytes:
        return b'/d_' + recode_base36_to_base64(self.cid)

    def get_view_command(self) -> str:
        return f'/v_{self.cid}'

    def get_internal_id(self):
        return self.doi


class NexusBooksHolder(BaseHolder):
    index_alias = 'nexus_books'

    def view_builder(self, user_language=None):
        return NexusBooksViewBuilder(document_holder=self, user_language=user_language)

    def buttons_builder(self, user_language, remote_request_link=None):
        return NexusBooksButtonsBuilder(document_holder=self, user_language=user_language)

    def get_download_command(self) -> bytes:
        return b'/d_' + recode_base36_to_base64(self.cid)

    def get_view_command(self) -> str:
        return f'/v_{self.cid}'

    def get_extension(self):
        return self.extension

    def get_internal_id(self):
        return self.cid
