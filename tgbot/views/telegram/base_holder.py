from urllib.parse import quote

import orjson
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
        if self.has_field('links'):
            if self.is_group_mode:
                el = el.add(self.get_ipfs_gateway_link(), escaped=True)
            else:
                el = el.add(self.get_view_command())
            need_pipe = True
        elif self.has_field('dois') and not self.is_group_mode:
            try:
                deep_link = encode_query_to_deep_link('#r ' + self.doi, request_context.bot_name)
                if with_librarian_service:
                    el = el.add(f'[request]({deep_link})', escaped=True)
                    need_pipe = True
            except TooLongQueryError:
                pass
        el = (
            el
            .add_external_provider_link(with_leading_pipe=need_pipe)
            .add_references_counter(bot_name=request_context.bot_name, with_leading_pipe=True)
            .add_filedata(show_filesize=True, with_leading_pipe=True)
            .build()
        )
        return el

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

    def get_mlt_command(self, cid) -> bytes:
        return b'/m_' + recode_base36_to_base64(cid)

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
