from urllib.parse import quote

import orjson

from library.document import (
    BaseDocumentHolder,
    LinksWrapper,
)

from .base_view_builder import (
    BaseButtonsBuilder,
    BaseViewBuilder,
)
from .common import (
    encode_link,
    get_formatted_filesize,
    recode_base36_to_base64,
)


class BaseTelegramDocumentHolder(BaseDocumentHolder):
    index_alias = 'nexus_science'

    def __init__(self, document, snippets=None):
        super().__init__(document)
        self.snippets = snippets

    @property
    def primary_link(self):
        if self.has_field('links') and self.links:
            links = LinksWrapper(self.links)
            return links.get_link_with_extension('pdf')

    @classmethod
    def create(cls, scored_document, snippets=None):
        return BaseTelegramDocumentHolder(orjson.loads(scored_document.document), snippets)

    def get_view_command(self) -> str:
        return f'/v_{self.links[0]["cid"]}'

    def get_formatted_filedata(self, show_format=True, show_language=True, show_filesize=False) -> str:
        parts = []
        if show_language:
            if self.languages:
                parts.append(' | '.join(self.languages).upper())
        if self.links:
            if show_format:
                all_extensions = set()
                for link in self.links:
                    all_extensions.add(link['extension'].upper())
                if all_extensions:
                    parts.extend(list(sorted(all_extensions)))
            if show_filesize and len(self.links) == 1 and self.links[0].get('filesize'):
                parts.append(get_formatted_filesize(self.links[0]['filesize']))
        return ' | '.join(parts)

    def get_ipfs_gateway_link(self):
        link = self.links[0]
        ipfs_link = (
            f'https://ipfs.io/ipfs/{link["cid"]}?'
            f'filename={quote(self.get_purified_name(link), safe="")}.{link["extension"]}'
        )
        return f'[IPFS.io]({ipfs_link})'

    def get_download_command(self, cid) -> bytes:
        return b'/d_' + recode_base36_to_base64(cid)

    def generate_tags_links(self, bot_name):
        if self.tags:
            links = [encode_link(bot_name, tag, f'tags:"{tag}"') for tag in self.tags]
            return links
        return []

    def view_builder(self, user_language=None):
        return BaseViewBuilder(document_holder=self, user_language=user_language)

    def get_doi_link(self):
        return f'[{self.doi}](https://doi.org/{quote(self.doi, safe="")})'

    def generate_remote_links(self):
        remote_links = []
        if self.links:
            remote_links.append(self.get_ipfs_gateway_link())
        if self.doi:
            remote_links.append(self.get_doi_link())
        if self.internal_iso:
            remote_links.append(f'[ISO.org](https://iso.org/standard/{self.internal_iso.split(":")[0]}.html)')
        return remote_links

    def buttons_builder(self, user_language, remote_request_link=None):
        return BaseButtonsBuilder(
            document_holder=self,
            user_language=user_language,
            remote_request_link=remote_request_link
        )
