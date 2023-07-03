from urllib.parse import quote

import orjson

from library.regexes.utils import cast_string_to_single_string

from .common import encode_link, get_formatted_filesize, recode_base36_to_base64
from .nexus_free import NexusFreeButtonsBuilder, NexusFreeViewBuilder
from .nexus_science import NexusScienceButtonsBuilder, NexusScienceViewBuilder


class BaseHolder:
    views_registry = {
        'nexus_free': NexusFreeViewBuilder,
        'nexus_science': NexusScienceViewBuilder,
    }

    def __init__(self, document, snippets=None):
        self.document = document
        self.snippets = snippets

    def __getattr__(self, name):
        if name in self.document:
            return self.document[name]
        elif 'metadata' in self.document and name in self.document['metadata']:
            return self.document['metadata'][name]
        elif 'id' in self.document and name in self.document['id']:
            return self.document['id'][name]

    def has_cover(self):
        return bool(self.isbns and len(self.isbns) > 0)

    @property
    def primary_link(self):
        if self.has_field('links') and self.links and self.links[0]['type'] == 'primary':
            return self.links[0]

    @classmethod
    def create(cls, scored_document, snippets=None):
        if scored_document.index_alias == 'nexus_free':
            return NexusFreeHolder(orjson.loads(scored_document.document), snippets)
        if scored_document.index_alias == 'nexus_science':
            return NexusScienceHolder(orjson.loads(scored_document.document), snippets)

    def get_view_command(self) -> str:
        return f'/v_{self.links[0]["cid"]}'

    def get_purified_name(self, link):
        limit = 55
        filename = cast_string_to_single_string(
            self.view_builder().add_authors(et_al=False).add_title(bold=False).add_formatted_datetime(
                with_months_for_recent=False).build().lower()
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

        return filename

    def get_formatted_filedata(self, show_format=True, show_language=True, show_filesize=False) -> str:
        parts = []
        if show_language:
            if self.language:
                parts.append(self.language.upper())
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

    def generate_remote_links(self):
        raise NotImplementedError()

    def get_download_command(self, cid) -> bytes:
        return b'/d_' + recode_base36_to_base64(cid)

    def generate_tags_links(self, bot_name):
        if self.tags:
            links = [encode_link(bot_name, tag, f'tags:"{tag}"') for tag in self.tags]
            return links
        return []

    def has_field(self, name):
        return (
            name in self.document
            or name in self.document.get('metadata', {})
        )


class NexusScienceHolder(BaseHolder):
    index_alias = 'nexus_science'

    def view_builder(self, user_language=None):
        return NexusScienceViewBuilder(document_holder=self, user_language=user_language)

    def get_doi_link(self):
        return f'[{self.doi}](https://doi.org/{quote(self.doi, safe="")})'

    def generate_remote_links(self):
        remote_links = []
        if self.links:
            remote_links.append(self.get_ipfs_gateway_link())
        if self.doi:
            remote_links.append(self.get_doi_link())
        return remote_links

    def buttons_builder(self, user_language, remote_request_link=None):
        return NexusScienceButtonsBuilder(
            document_holder=self,
            user_language=user_language,
            remote_request_link=remote_request_link
        )

    def get_internal_id(self):
        return self.doi

    def get_purified_name(self, link):
        return super().get_purified_name(link) or quote(self.doi, safe='')


class NexusFreeHolder(BaseHolder):
    index_alias = 'nexus_free'

    def view_builder(self, user_language=None):
        return NexusFreeViewBuilder(document_holder=self, user_language=user_language)

    def buttons_builder(self, user_language, remote_request_link=None):
        return NexusFreeButtonsBuilder(document_holder=self, user_language=user_language)

    def generate_remote_links(self):
        remote_links = []
        if self.links:
            remote_links.append(self.get_ipfs_gateway_link())
        if self.internal_iso:
            remote_links.append(f'[ISO.org](https://iso.org/standard/{self.internal_iso.split(":")[0]}.html)')
        return remote_links

    def get_internal_id(self):
        return self.links[0]["cid"]

    def get_purified_name(self, link):
        return super().get_purified_name(link) or link['cid']

    def has_field(self, name):
        return super().has_field(name) or name in self.document.get('id', {})
