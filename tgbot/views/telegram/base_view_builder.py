import datetime
import hashlib
import math
import re
from html import unescape
from typing import Optional
from urllib.parse import quote

import bleach
from bs4 import BeautifulSoup
from izihawa_types.datetime import CustomDatetime
from izihawa_types.safecast import safe_int
from telethon import Button

from library.telegram.common import close_button
from library.textutils.utils import (
    despace_full,
    escape_format,
)
from tgbot.markdownifytg import (
    highlight_md_converter,
    md_converter,
)
from tgbot.translations import t

from ...search_request_builder import get_type_icon
from .common import (
    TooLongQueryError,
    add_expand_dot,
    encode_query_to_deep_link,
    get_formatted_filesize, fix_markdown,
)

preprints = {'10.1101', '10.21203'}


def highlight_markdown_snippet(snippet, wrapper_bold_open=b'**', wrapper_bold_close=b'**'):
    markdowned = b''
    start_from = 0
    for highlight in snippet.highlights:
        from_ = getattr(highlight, 'from')
        to = highlight.to
        markdowned += escape_format(snippet.fragment[start_from:from_])
        markdowned += wrapper_bold_open
        markdowned += escape_format(snippet.fragment[from_:to])
        markdowned += wrapper_bold_close
        start_from = to
    markdowned += escape_format(snippet.fragment[start_from:])
    markdowned = markdowned.decode()
    markdowned = despace_full(re.sub(r'\n+', ' ', markdowned))
    if markdowned[0].islower() or (markdowned[:2] == '**' and markdowned[2].islower()):
        markdowned = '...' + markdowned
    markdowned = markdowned + '...'
    return markdowned


def highlight_html_snippet(snippet):
    return highlight_markdown_snippet(snippet, b'<highlight>', b'</highlight>')


def replace_broken_tags(abstract):
    return abstract.replace('<disp-formula>', '<formula>').replace('</disp-formula>', '</formula>')


def despace_abstract(abstract):
    return re.sub(r'\n*(</?[^>]+/?>)\n*', r'\g<1>', abstract)


def plain_author(author, bot_name=None):
    text = None
    if 'family' in author and 'given' in author:
        text = f"{author['given']} {author['family']}"
    elif 'family' in author or 'given' in author:
        text = author.get('family') or author.get('given')
    elif 'name' in author:
        text = author['name']
    if text and 'orcid' in author and bot_name:
        orcid_query = encode_query_to_deep_link(f"authors.orcid:\"{author['orcid']}\"", bot_name)
        text = f'[{text}]({orcid_query})'
    return text


class TextPart:
    def __init__(self, part):
        self.part = str(part)
        self._bold = False
        self._italic = False
        self._brackets = False
        self._escaped = False
        self._clickable = False
        self._unbreakable = False

    def escaped(self):
        self._escaped = True
        return self

    def bold(self):
        self._bold = True
        return self

    def italic(self):
        self._italic = True
        return self

    def within_brackets(self):
        self._brackets = True
        return self

    def clickable(self):
        self._clickable = True
        return self

    def unbreakable(self):
        self._unbreakable = True
        return self

    def limits(self, limit, with_dots: bool = False):
        if len(self.part) > limit:
            if self._unbreakable:
                self.part = ''
            else:
                self.part = self.part[:limit]
                # If part ends with link
                if incomplete_link_1 := re.search(r'(\[)[^]]*]\s*\([^)]*$', self.part):
                    self.part = self.part[:incomplete_link_1.start(1) - 1]
                elif incomplete_link_2 := re.search(r'(\[)[^]]*$', self.part):
                    self.part = self.part[:incomplete_link_2.start(1) - 1]
                if with_dots:
                    self.part += '...'

    def __add__(self, other):
        self.part += str(other)

    def __len__(self):
        return len(self.part)

    def __str__(self):
        r = self.part
        if not self._escaped:
            r = escape_format(r)
        if self._clickable:
            r = f'`{r}`'
        if self._brackets:
            r = f'({r})'
        if self._bold:
            r = f'**{r}**'
        if self._italic:
            r = f'__{r}__'
        return r


class BaseViewBuilder:
    def __init__(self, document_holder, user_language):
        self.document_holder = document_holder
        self.user_language = user_language
        self.last_limit_part = None
        self.last_limit = None
        self.parts = []

    def has_field(self, name):
        return self.document_holder.has_field(name)

    def add(self, el, bold=False, italic=False, escaped=False, clickable=False, lower=False, with_brackets=False, unbreakable=False,
            eol: Optional[str] = ' '):
        if el:
            if not isinstance(el, TextPart):
                el = TextPart(el if not lower else el.lower())
                if bold:
                    el.bold()
                if italic:
                    el.italic()
                if escaped:
                    el.escaped()
                if clickable:
                    el.clickable()
                if with_brackets:
                    el.within_brackets()
                if unbreakable:
                    el.unbreakable()
            self.parts.append(el)
            if eol is not None:
                self.parts.append(TextPart(eol))
        return self

    def add_snippet(self, on_newline=True):
        snippet = None
        text = None

        if self.document_holder.snippets:
            snippet = self.document_holder.snippets.get('abstract') or self.document_holder.snippets.get('content')

        is_snippet = snippet and snippet.highlights

        if is_snippet:
            text = snippet
            text = highlight_html_snippet(text)
            text = bleach.clean(text, tags=['abstract', 'content', 'highlight'], strip=True, strip_comments=True)
        elif abstract := self.document_holder.abstract or self.document_holder.content:
            text = abstract
            text = replace_broken_tags(text)
            text = bleach.clean(text, tags=['abstract', 'content', 'figure', 'img'], strip=True, strip_comments=True)

        if not text:
            return self

        soup = BeautifulSoup(text)
        for tag in list(soup.select('figure, img, [role="note"], a[href^="#"], .side-box-text')):
            tag.extract()
        text = highlight_md_converter.convert_soup(soup)
        text = re.sub('\n+', ' ', text).strip()

        if not text:
            return self

        text = fix_markdown(add_expand_dot(text, 360))
        text = f'__{text}__'

        if on_newline:
            self.add_new_line()
        self.add(text, escaped=True)

        return self

    def add_metadata(self, bot_name, on_newline=True):
        self.add_isbns(on_newline=on_newline, label=True)
        if self.document_holder.publisher:
            try:
                query = encode_query_to_deep_link(f'pub:"{self.document_holder.publisher}"', bot_name=bot_name)
                self.add_new_line().add('Publisher:', bold=True).add(
                    f'[{self.document_holder.publisher}]({query})',
                    escaped=True,
                )
            except TooLongQueryError:
                self.add_new_line().add('Publisher:', bold=True).add(
                    self.document_holder.publisher,
                    escaped=True,
                )
        if self.document_holder.dois and len(self.document_holder.dois) > 1:
            links = ', '.join([f'[{doi}](https://doi.org/{quote(doi)})' for doi in self.document_holder.dois[1:]])
            self.add_new_line().add('Additional DOIs:', bold=True).add(
                links,
                escaped=True,
            )
        if self.document_holder.series:
            try:
                query = encode_query_to_deep_link(f'ser:"{self.document_holder.series}"', bot_name=bot_name)
                self.add_new_line().add('Series:', bold=True).add(
                    f'[{self.document_holder.series}]({query})',
                    escaped=True,
                )
            except TooLongQueryError:
                self.add_new_line().add('Series:', bold=True).add(
                    self.document_holder.series,
                    escaped=True,
                )
        return self

    def limits(self, limit=None, with_dots: bool = False):
        if limit:
            current_length = 0
            for i, part in enumerate(self.parts):
                non_displaying_length = 0
                for match in re.finditer(r'\[[^]]*]\s*(\([^)]*\))$', part.part):
                    non_displaying_length += len(match.group(1))
                part_len = len(part) - non_displaying_length
                current_length += part_len
                if current_length > limit:
                    part.limits(limit + len(part) - current_length, with_dots=with_dots)
                    if len(part) > 0:
                        self.parts = self.parts[:i + 1]
                    else:
                        self.parts = self.parts[:i]
                    return self
        return self

    def limited(self, limit):
        self.last_limit_part = len(self.parts)
        self.last_limit = limit
        return self

    def end_limited(self, with_dots: bool = False):
        if self.last_limit is not None:
            current_length = 0
            for i, part in enumerate(self.parts[self.last_limit_part:]):
                current_length += len(part)
                if current_length > self.last_limit:
                    part.limits(current_length - self.last_limit, with_dots=with_dots)
                    if len(part) > 0:
                        self.parts = self.parts[:self.last_limit_part + i + 1]
                    else:
                        self.parts = self.parts[:self.last_limit_part + i]
                    return self
            self.last_limit = None
            self.last_limit_part = None
        return self

    def add_icon(self, with_cover=False, with_hidden_id=False):
        icon = get_type_icon(self.document_holder.type)
        if with_hidden_id:
            icon = f'[{icon}](https://standard-template-construct.org/#/nexus_science/{quote(self.document_holder.get_internal_id())})'
        elif with_cover and self.document_holder.isbns:
            icon = f'[{icon}](https://covers.openlibrary.org/b/isbn/{self.document_holder.isbns[0]}-L.jpg)'
        return self.add(icon, escaped=True)

    def add_label(self, label_name, bold=True, lower=False):
        return self.add(t(label_name, self.user_language) + ':', bold=bold, lower=lower)

    def add_new_line(self, n: int = 1):
        return self.add('\n' * n, eol=None)

    def add_formatted_datetime(self, with_months_for_recent=True):
        if self.has_field('issued_at') and self.document_holder.issued_at != -62135596800:
            dt = CustomDatetime.from_timestamp(self.document_holder.issued_at)
            try:
                ct = datetime.date(dt.year, dt.month, 1)
                if with_months_for_recent and datetime.date.today() - datetime.timedelta(days=365) < ct:
                    self.add(TextPart(f'{dt.year}.{dt.month:02d}').within_brackets())
                else:
                    self.add(TextPart(str(dt.year)).within_brackets())
            except ValueError:
                pass
        return self

    def add_downloads_count(self):
        return self.add(f'{math.log1p(self.document_holder.downloads_count):.1f}')

    def add_references_counter(self, bot_name, with_leading_pipe=False):
        if self.has_field('referenced_by_count') and self.document_holder.referenced_by_count:
            if with_leading_pipe:
                self.add('|')
            text = f'🔗 {self.document_holder.referenced_by_count}'
            if self.document_holder.doi:
                try:
                    link = encode_query_to_deep_link(f'rd:{self.document_holder.doi}', bot_name=bot_name)
                    text = f'[{text}]({link})'
                except TooLongQueryError:
                    pass
            self.add(text, escaped=True)
        return self

    def add_doi_link(self, with_leading_pipe=False, on_newline=False, label=False, text=None, is_short_text=False):
        if self.document_holder.doi:
            if on_newline:
                self.add_new_line()
            if with_leading_pipe:
                self.add('|')

            if label:
                if isinstance(label, str):
                    self.add(label, bold=True)
                else:
                    self.add('DOI:', bold=True)
            escaped_doi = escape_format(self.document_holder.doi)
            if text is None:
                if is_short_text:
                    text = 'doi.org'
                else:
                    text = self.document_holder.doi
            self.add(f'[{text}](https://doi.org/{quote(escaped_doi)})', escaped=True)
            return True

    def add_iso_link(self, with_leading_pipe=False, on_newline=False, label=False, text=None, is_short_text=False):
        if self.document_holder.iso_id and self.document_holder.internal_iso:
            if on_newline:
                self.add_new_line()
            if with_leading_pipe:
                self.add('|')

            if label:
                if isinstance(label, str):
                    self.add(label, bold=True)
                else:
                    self.add('ISO:', bold=True)
            if text is None:
                if is_short_text:
                    text = 'iso.org'
                else:
                    text = self.document_holder.iso_id.upper()
            self.add(f'[{text}](https://iso.org/standard/{self.document_holder.internal_iso.split(":")[0]}.html)', escaped=True)
            return True

    def add_pubmed_link(self, with_leading_pipe=False, on_newline=False, label=False, text=None, is_short_text=False):
        if self.document_holder.pubmed_id:
            if on_newline:
                self.add_new_line()
            if with_leading_pipe:
                self.add('|')

            if label:
                if isinstance(label, str):
                    self.add(label, bold=True)
                else:
                    self.add('PubMed:', bold=True)
            if text is None:
                if is_short_text:
                    text = 'pubmed'
                else:
                    text = f'PMID:{self.document_holder.pubmed_id}'
            self.add(f'[{text}](https://pubmed.ncbi.nlm.nih.gov/{self.document_holder.pubmed_id}/)', escaped=True)
            return True

    def add_wiki_link(self, label=None, text=None, is_short_text=False):
        if self.document_holder.wiki:
            self.add_new_line()
            if label:
                if isinstance(label, str):
                    self.add(label, bold=True)
                else:
                    self.add('Wikipedia:', bold=True)
            if text is None:
                if is_short_text:
                    text = 'Wikipedia:'
                else:
                    text = self.document_holder.title
            self.add(f'[{text}]({self.document_holder.get_wikipedia_link()})', escaped=True)
        return self

    def add_external_provider_link(self, with_leading_pipe=False, on_newline=False, label=False, text=None, is_short_text=False, end_newline=False):
        has_link = (
            self.add_doi_link(with_leading_pipe=with_leading_pipe, on_newline=on_newline, label=label, text=text, is_short_text=is_short_text)
            or self.add_iso_link(with_leading_pipe=with_leading_pipe, on_newline=on_newline, label=label, text=text, is_short_text=is_short_text)
            or self.add_pubmed_link(with_leading_pipe=with_leading_pipe, on_newline=on_newline, label=label, text=text, is_short_text=is_short_text)
        )
        if end_newline and has_link:
            self.add_new_line()
        return self

    def add_links(self):
        on_newline = False
        if remote_links := self.document_holder.generate_remote_links():
            self.add_label("LINKS")
            self.add(" - ".join(remote_links), escaped=True)
            on_newline = True
        self.add_external_provider_link(label=True, on_newline=on_newline)
        return self

    def add_tags(self, bot_name):
        tag_links = self.document_holder.generate_tags_links(bot_name)
        if not tag_links:
            return self
        self.add(tag_links[0], escaped=True, unbreakable=True)
        for tag_link in tag_links[1:]:
            self.add('- ' + tag_link, escaped=True, unbreakable=True)
        return self

    def add_authors(self, et_al=True, first_n_authors=1, on_newline=True, bot_name=None):
        if not self.document_holder.authors:
            return self

        authors = [plain_author(author, bot_name) for author in self.document_holder.authors]
        authors = [author for author in authors if bool(author)]

        if not authors:
            return self

        if on_newline:
            self.add_new_line()

        self.add('; '.join(authors[:first_n_authors]) + (' et al' if len(authors) > first_n_authors and et_al else ''), escaped=True)
        return self

    def add_short_description(self, with_hidden_id: bool = False):
        return (
            self.add_icon(with_hidden_id=with_hidden_id)
                .add_title()
                .limits(250, with_dots=True)
                .add_locator()
        )

    def add_view(self, bot_name):
        abstract_limit = 3000
        all_limit = 4000
        view = (
            self.add_icon(with_cover=True)
                .add_title()
                .limits(400, with_dots=True)
                .add_locator(first_n_authors=3, bot_name=bot_name)
                .add_new_line(2)
                .add_stats()
                .add_links()
                .add_wiki_link(label=True)
                .add_metadata(bot_name=bot_name)
                .add_new_line(2)
                .add_abstract(bot_name=bot_name)
                .limits(abstract_limit, with_dots=True)
                .add_new_line(2)
                .add_tags(bot_name=bot_name)
                .limits(all_limit)
        )
        return view

    def add_isbns(self, on_newline=False, label=False, end_newline=False):
        if isbns := self.document_holder.isbns or self.document_holder.parent_isbns:
            if on_newline:
                self.add_new_line()
            if label:
                self.add('ISBN:', bold=True)
            self.add(', '.join(isbns[:2]))
            if end_newline:
                self.add_new_line()
        return self

    def build(self):
        text = ''.join(map(str, self.parts)).strip()
        text = re.sub('\n\n+', '\n\n', text)
        return text

    def add_edition(self, with_brackets=True, bold=False):
        edition = self.document_holder.edition
        if edition == '1':
            return self
        if edition:
            if edition.isdigit():
                if edition[-1] == '1':
                    edition += 'st edition'
                elif edition[-1] == '2':
                    edition += 'nd edition'
                elif edition[-1] == '3':
                    edition += 'rd edition'
                else:
                    edition += 'th edition'
        return self.add(edition, with_brackets=with_brackets, bold=bold)

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
            self.add(f'pp. {self.document_holder.last_page}')
        return self

    def add_container(self, bold=False, italic=False):
        if self.document_holder.container_title:
            self.add('in')
            self.add(self.document_holder.container_title, bold=bold, italic=italic)
        self.add_volume(bold=bold, italic=italic)
        return self

    def add_volume(self, bold=False, italic=False):
        if self.document_holder.volume:
            if self.document_holder.issue:
                self.add(f'vol. {self.document_holder.volume}({self.document_holder.issue})', bold=bold, italic=italic)
            else:
                if safe_int(self.document_holder.volume):
                    self.add(f'vol. {self.document_holder.volume}', bold=bold, italic=italic)
                else:
                    self.add(self.document_holder.volume, bold=bold, italic=italic)
        elif self.document_holder.periodical:
            self.add(self.document_holder.periodical, bold=bold, italic=italic)
        return self

    def add_title(self, bold=True):
        text_title = BeautifulSoup(self.document_holder.title or '', 'lxml').get_text(separator='').replace('\n', ' ')
        title = text_title
        if self.document_holder.iso_id:
            title = f'{self.document_holder.iso_id.upper()}'
            if text_title:
                title += f' - {text_title}'
        elif self.document_holder.bs_id:
            title = f'{self.document_holder.bs_id.upper()}'
            if text_title:
                title += f' - {text_title}'
        if not title and self.document_holder.doi:
            title = self.document_holder.doi
        self.add(title, bold=bold)
        self.add_edition(with_brackets=True, bold=bold)

        return self

    def add_locator(self, first_n_authors=1, markup=True, bot_name=None):
        return (
            self.add_authors(first_n_authors=first_n_authors, bot_name=bot_name)
                .add_container(italic=markup)
                .add_pages()
                .add_formatted_datetime()
        )

    def add_filedata(self, show_filesize=False, with_leading_pipe=False):
        filedata = self.document_holder.get_formatted_filedata(show_filesize=show_filesize)
        if filedata:
            if with_leading_pipe:
                self.add('|')
            self.add(filedata)
        return self

    def add_abstract(self, bot_name):
        abstract = self.document_holder.abstract or ''
        if self.document_holder.type == 'wiki':
            abstract += self.document_holder.content or ''
        if abstract:
            text = replace_broken_tags(despace_abstract(abstract or ''))
            soup = BeautifulSoup(text, 'html.parser')
            for tag in list(soup.select('figure, img, [role="note"], .side-box-text, .thumbcaption')):
                tag.extract()
            for tag in soup.find_all('i'):
                i_tag = soup.new_tag('i')
                i_tag.append(tag.get_text())
                tag.replace_with(i_tag)
            for tag in soup.find_all('b'):
                b_tag = soup.new_tag('b')
                b_tag.append(tag.get_text())
                tag.replace_with(b_tag)
            for tag in soup.find_all('h1, h2, h3, h4, h5, h6, header'):
                tag.name = 'b'
            if self.document_holder.type == 'wiki':
                for tag in list(soup.find_all('summary, details')):
                    tag.unwrap()
                for tag in list(soup.find_all('a')):
                    if tag.attrs['href'].startswith('#'):
                        tag.extract()
                    elif '://' not in tag.attrs['href']:
                        wiki_md5 = hashlib.md5(('A/' + tag.attrs['href']).encode()).hexdigest().lower()
                        deep_query = encode_query_to_deep_link(f'id.wiki:{wiki_md5}', bot_name=bot_name)
                        if deep_query:
                            tag.attrs['href'] = deep_query
                        else:
                            tag.attrs['href'] = self.document_holder.get_wikipedia_link(title=tag.attrs['href'])
                    text = tag.get_text()
                    tag.clear()
                    tag.append(text)
                for tag in list(soup.find_all('blockquote')):
                    text = tag.get_text()
                    tag.clear()
                    tag.append(text)
                abstract = md_converter.convert(escape_format(str(soup), escape_font=False))
            else:
                abstract = unescape(escape_format(md_converter.convert_soup(soup), escape_font=False))
            abstract = re.sub('\n{3,}', '\n\n', abstract)
            self.add(abstract.strip(), escaped=True)
        return self

    def add_stats(self, end_newline=True):
        if self.document_holder.page_rank and abs(self.document_holder.page_rank - 0.15) > 0.001:
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


class BaseButtonsBuilder:
    buttons_in_row = 3

    def __init__(self, document_holder, user_language, remote_request_link=None):
        self.document_holder = document_holder
        self.user_language = user_language
        self.remote_request_link = remote_request_link
        self.buttons = [[]]

    def add_button(self, button):
        if len(self.buttons[-1]) >= self.buttons_in_row:
            self.buttons.append([])
        self.buttons[-1].append(button)

    def add_back_button(self, back_command):
        self.add_button(Button.inline(
            text='⬅️',
            data=back_command
        ))
        return self

    def add_download_button(self):
        # ⬇️ is a mark, Find+F over sources before replacing
        if not self.document_holder.links:
            return self
        for link in self.document_holder.links:
            label = [link["extension"].upper()]
            if link.get('filesize'):
                label.append(get_formatted_filesize(link["filesize"]))
            self.add_button(Button.inline(
                text=f'⬇️ {" | ".join(label)}',
                data=self.document_holder.get_download_command(link['cid']),
            ))
            if len(self.buttons[-1]) > self.buttons_in_row:
                self.buttons.append([])
        return self

    def add_mlt_button(self):
        mlt_command = self.document_holder.get_mlt_command()
        if mlt_command:
            self.add_button(Button.inline(
                text=f'🖲️ {t("SIMILAR", language=self.user_language)}',
                data=mlt_command,
            ))
        return self

    def add_read_more_button(self):
        if self.document_holder.type == 'wiki':
            self.add_button(Button.url(
                text=f'🌍 {t("READ_MORE", language=self.user_language)}',
                url=self.document_holder.get_wikipedia_link(),
            ))
        return self

    def add_remote_download_button(self, bot_name):
        # ⬇️ is a mark, Find+F over sources before replacing
        if not self.document_holder.links:
            return self
        try:
            internal_id = self.document_holder.get_internal_id()
            internal_id = internal_id.replace('id.dois', 'doi')
            encoded_query = encode_query_to_deep_link(internal_id, bot_name)
            self.add_button(Button.url('⬇', encoded_query))
        except TooLongQueryError:
            pass
        return self

    def add_remote_request_button(self):
        if self.remote_request_link:
            self.add_button(Button.url('🤌', self.remote_request_link))
        return self

    def add_close_button(self):
        self.add_button(close_button())
        return self

    def build(self):
        return self.buttons

    def add_linked_search_button(self, bot_name):
        if self.document_holder.referenced_by_count:
            try:
                self.add_button(Button.url(
                    text=f'🔗 {self.document_holder.referenced_by_count or ""}',
                    url=encode_query_to_deep_link(f'rd:{self.document_holder.doi}', bot_name=bot_name),
                ))
            except TooLongQueryError:
                pass
        return self

    def add_journal_search(self, bot_name):
        try:
            if self.document_holder.has_field('issns'):
                issn_query = f'issns:"{self.document_holder.issns[0]}" order_by:date'
                self.add_button(Button.url(
                    text='📰',
                    url=encode_query_to_deep_link(issn_query, bot_name=bot_name),
                ))
        except TooLongQueryError:
            pass
        return self

    def add_default_layout(self, bot_name, position: int = 0, is_group_mode: bool = False):
        if is_group_mode:
            return (
                self.add_remote_download_button(bot_name)
                    .add_linked_search_button(bot_name)
                    .add_journal_search(bot_name)
                    .add_read_more_button()
                    .add_close_button()
            )
        else:
            return (
                self.add_download_button()
                    .add_remote_request_button()
                    .add_linked_search_button(bot_name)
                    .add_journal_search(bot_name)
                    .add_read_more_button()
                    .add_mlt_button()
                    .add_close_button()
            )
