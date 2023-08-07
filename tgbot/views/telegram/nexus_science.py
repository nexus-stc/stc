from html import unescape

from bs4 import BeautifulSoup
from izihawa_types.safecast import safe_int
from telethon import Button

from library.textutils.utils import escape_format

from ...markdownifytg import md_converter
from .base_view_builder import (
    BaseButtonsBuilder,
    BaseViewBuilder,
)
from .common import (
    TooLongQueryError,
    encode_query_to_deep_link,
)

preprints = {'10.1101', '10.21203'}


class NexusScienceButtonsBuilder(BaseButtonsBuilder):
    def add_linked_search_button(self, bot_name):
        if self.document_holder.referenced_by_count:
            try:
                self.buttons[-1].append(
                    Button.url(
                        text=f'🔗 {self.document_holder.referenced_by_count or ""}',
                        url=encode_query_to_deep_link(f'rd:{self.document_holder.doi}', bot_name=bot_name),
                    )
                )
            except TooLongQueryError:
                pass
        return self

    def add_journal_search(self, bot_name):
        try:
            if self.document_holder.has_field('issns'):
                issn_query = f'issns:"{self.document_holder.issns[0]}" order_by:date'
                self.buttons[-1].append(
                    Button.url(
                        text='📰',
                        url=encode_query_to_deep_link(issn_query, bot_name=bot_name),
                    )
                )
        except TooLongQueryError:
            pass
        return self

    def add_default_layout(self, bot_name, position: int = 0, is_group_mode: bool = False):
        if is_group_mode:
            return (
                self.add_remote_download_button(bot_name)
                    .add_linked_search_button(bot_name)
                    .add_journal_search(bot_name)
                    .add_close_button()
            )
        else:
            return (
                self.add_download_button()
                    .add_remote_request_button()
                    .add_linked_search_button(bot_name)
                    .add_journal_search(bot_name)
                    .add_close_button()
            )


class NexusScienceViewBuilder(BaseViewBuilder):
    def is_preprint(self):
        return self.document_holder.doi.split('/')[0] in preprints

    def add_pages(self):
        if self.document_holder.first_page:
            if self.document_holder.last_page:
                if self.document_holder.first_page == self.document_holder.last_page:
                    self.add(f'p. {self.document_holder.first_page}')
                else:
                    self.add(f'pp. {self.document_holder.first_page}-{self.document_holder.last_page}')
            else:
                self.add(f'p. {self.document_holder.first_page}')
        elif self.document_holder.last_page:
            self.add(f'p. {self.document_holder.last_page}')
        return self

    def add_container(self, bold=False, italic=False):
        if self.document_holder.container_title:
            self.add('in')
            self.add(self.document_holder.container_title, bold=bold, italic=italic)
        return self

    def add_volume(self):
        if self.document_holder.volume:
            if self.document_holder.issue:
                self.add(f'vol. {self.document_holder.volume}({self.document_holder.issue})')
            else:
                if safe_int(self.document_holder.volume):
                    self.add(f'vol. {self.document_holder.volume}')
                else:
                    self.add(self.document_holder.volume)
        return self

    def add_title(self, bold=True):
        title = BeautifulSoup(self.document_holder.title or '', 'lxml').text
        self.add(title or self.document_holder.doi, bold=bold)
        return self

    def add_locator(self, first_n_authors=1, markup=True, bot_name=None):
        return (
            self.add_authors(first_n_authors=first_n_authors, bot_name=bot_name)
                .add_container(italic=markup)
                .add_formatted_datetime()
                .add_pages()
        )

    def add_filedata(self, show_filesize=False, with_leading_pipe=False):
        filedata = self.document_holder.get_formatted_filedata(show_filesize=show_filesize)
        if filedata:
            if with_leading_pipe:
                self.add('|')
            self.add(filedata)
        return self

    def add_abstract(self):
        if self.document_holder.abstract:
            soup = BeautifulSoup(self.document_holder.abstract.replace('</header>\n', '</header>') or '', 'html.parser')
            abstract = escape_format(unescape(md_converter.convert_soup(soup)), escape_font=False)
            self.add(abstract.strip(), escaped=True)
        return self

    def add_stats(self, end_newline=True):
        if self.document_holder.page_rank:
            star_rank = int(round(min(self.document_holder.page_rank, 1) * 5)) * '⭐'
            if star_rank:
                self.add(f'**Rank**: {star_rank}', escaped=True)
            else:
                self.add('**Rank**: ❔', escaped=True)
            if end_newline:
                self.add_new_line()
        return self

    def add_doi(self, clickable=True, with_brackets=False, with_leading_pipe=False):
        if self.document_holder.doi:
            if with_leading_pipe:
                self.add('|')
            return self.add(self.document_holder.doi, clickable=clickable, with_brackets=with_brackets)
