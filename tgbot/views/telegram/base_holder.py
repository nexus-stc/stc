import urllib
from typing import Optional
from urllib.parse import quote

import orjson
from bs4 import BeautifulSoup
from stc_geck.advices import BaseDocumentHolder

from library.textutils.utils import cast_string_to_single_string

from .base_view_builder import (
    BaseButtonsBuilder,
    BaseViewBuilder,
)
from .common import (
    TooLongQueryError,
    encode_link,
    encode_query_to_deep_link,
    get_formatted_filesize,
    recode_base36_to_base64,
)


class BaseTelegramDocumentHolder(BaseDocumentHolder):
    index_alias = 'nexus_science'

    def __init__(self, document, snippets=None):
        super().__init__(document)
        self.snippets = snippets

    @classmethod
    def create(cls, scored_document, snippets=None):
        return BaseTelegramDocumentHolder(orjson.loads(scored_document.document), snippets)

    def base_render(self, request_context, with_librarian_service):
        el = (
            self
            .view_builder(request_context.chat['language'])
            .add_short_description()
            .add_snippet()
            .add_new_line()
        )
        need_pipe = False
        request_link = False
        if not self.has_field('links') and not self.is_group_mode and with_librarian_service:
            try:
                if self.has_field('dois'):
                    deep_link = encode_query_to_deep_link('#r ' + self.doi, request_context.bot_name)
                elif self.has_field('internal_iso'):
                    deep_link = encode_query_to_deep_link(f'#r id.internal_iso:"{self.internal_iso}"', request_context.bot_name)
                elif self.has_field('pubmed_id'):
                    deep_link = encode_query_to_deep_link(f'#r id.pubmed_id:{self.pubmed_id}', request_context.bot_name)
                else:
                    deep_link = None
                if deep_link:
                    request_link = True
                    el = el.add(f'[request]({deep_link})', escaped=True)
                    need_pipe = True
            except TooLongQueryError:
                pass
        if not request_link and (not self.is_group_mode or self.has_field('links')):
            el = el.add(self.get_view_command(bot_name=request_context.bot_name), escaped=True)
            need_pipe = True
        el = (
            el
            .add_external_provider_link(with_leading_pipe=need_pipe, is_short_text=True)
            .add_references_counter(bot_name=request_context.bot_name, with_leading_pipe=True)
            .add_filedata(show_filesize=True, with_leading_pipe=True)
            .build()
        )
        return el

    def get_view_command(self, bot_name) -> str:
        link = self.get_link(bot_name=bot_name, label='view')
        if link:
            return link
        elif self.has_field('links'):
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
        ipfs_link = (
            f'https://libstc.cc/#/nexus_science/{urllib.parse.quote_plus(self.get_internal_id())}'
        )
        return f'[LibSTC.cc]({ipfs_link})'

    def get_download_command(self, cid) -> bytes:
        return b'/d_' + recode_base36_to_base64(cid)

    def get_mlt_command(self) -> bytes:
        try_internal_id = self.get_internal_id().encode()
        if len(try_internal_id) < 62:
            return b'/n_' + try_internal_id
        for link in self.get_links().links.values():
            return b'/m_' + recode_base36_to_base64(link['cid'])

    def generate_tags_links(self, bot_name):
        if self.tags:
            links = [encode_link(bot_name, tag, f'tags:"{tag}"') for tag in self.tags]
            return links
        elif self.category:
            return [encode_link(bot_name, self.category, f'metadata.category:"{self.category}"')]
        return []

    def view_builder(self, user_language=None):
        return BaseViewBuilder(document_holder=self, user_language=user_language)

    def get_doi_link(self):
        return f'[{self.doi}](https://doi.org/{quote(self.doi, safe="")})'

    def generate_remote_links(self):
        remote_links = []
        if self.links:
            remote_links.append(self.get_ipfs_gateway_link())
        return remote_links

    def buttons_builder(self, user_language, remote_request_link=None):
        return BaseButtonsBuilder(
            document_holder=self,
            user_language=user_language,
            remote_request_link=remote_request_link
        )

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

        if not filename and self.doi:
            filename = quote(self.doi, safe='')
        if not filename:
            filename = link['cid']
        return filename

    def get_wikipedia_link(self, host: str = 'en.wikipedia-on-ipfs.org', title: Optional[str] = None):
        if not title:
            title = self.title
        return f'https://{host}/wiki/{quote(title.replace(" ", "_"))}'

    def get_title_with_link(self, bot_name, title=None):
        title = title or self.title
        title = BeautifulSoup(title or '', 'lxml').get_text(separator='')
        internal_id = self.get_internal_id()
        link = self.get_link(bot_name=bot_name, internal_id=internal_id, label=title)
        if link:
            return link
        else:
            return f'{title} - `{internal_id}`)'

    def get_link(self, bot_name, label=None, internal_id=None):
        internal_id = internal_id or self.get_internal_id()
        try:
            deep_query = encode_query_to_deep_link(internal_id, bot_name)
        except TooLongQueryError:
            if not self.has_field('links'):
                return
            cid_encoded = recode_base36_to_base64(self.document['links'][0]["cid"]).decode()
            deep_query = encode_query_to_deep_link(cid_encoded, bot_name, skip_encoding=True)
        return f'[{label or internal_id}]({deep_query})'
