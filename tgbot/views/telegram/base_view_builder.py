import datetime
import math
import re
from typing import Optional
from urllib.parse import quote

from izihawa_types.datetime import CustomDatetime
from telethon import Button

from library.regexes.utils import despace_full, escape_format
from library.telegram.common import close_button
from tgbot.translations import t

from ...app.query_builder import get_type_icon
from .common import TooLongQueryError, add_expand_dot, encode_query_to_deep_link, get_formatted_filesize


def highlight_markdown(snippet):
    markdowned = b''
    start_from = 0
    for highlight in snippet.highlights:
        from_ = getattr(highlight, 'from')
        to = highlight.to
        markdowned += escape_format(snippet.fragment[start_from:from_])
        markdowned += b'**'
        markdowned += escape_format(snippet.fragment[from_:to])
        markdowned += b'**'
        start_from = to
    markdowned += escape_format(snippet.fragment[start_from:])
    markdowned = markdowned.decode()
    markdowned = despace_full(re.sub(r'\n+', ' ', markdowned))
    if markdowned[0].islower() or (markdowned[:2] == '**' and markdowned[2].islower()):
        markdowned = '...' + markdowned
    markdowned = markdowned + '...'
    markdowned = f'__{markdowned}__'
    return markdowned


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
        snippet = self.document_holder.snippets.get('abstract')
        if snippet and snippet.highlights:
            if on_newline:
                self.add_new_line()
            self.add(highlight_markdown(snippet), escaped=True)
        elif abstract := self.document_holder.abstract:
            if on_newline:
                self.add_new_line()
            abstract = add_expand_dot(abstract, 140)
            abstract = f'__{abstract}__'
            self.add(abstract, escaped=True)
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
                current_length += len(part)
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

    def add_icon(self, with_cover=False):
        icon = get_type_icon(self.document_holder.type)
        if with_cover and self.document_holder.isbns:
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

    def add_external_provider_link(self, with_leading_pipe=False, on_newline=False, label=False, text=None, end_newline=False):
        if self.document_holder.doi or (self.document_holder.iso_id and self.document_holder.internal_iso):
            if on_newline:
                self.add_new_line()
            if with_leading_pipe:
                self.add('|')

        if self.document_holder.doi:
            if label:
                self.add('DOI:', bold=True)
            escaped_doi = escape_format(self.document_holder.doi)
            if text is None:
                text = 'doi.org'
            self.add(f'[{text}](https://doi.org/{quote(escaped_doi)})', escaped=True)

            if end_newline:
                self.add_new_line()
        elif self.document_holder.iso_id and self.document_holder.internal_iso:
            if label:
                self.add('ISO:', bold=True)
            if text is None:
                text = 'iso.org'
            self.add(f'[{text}](https://iso.org/standard/{self.document_holder.internal_iso.split(":")[0]}.html)', escaped=True)

            if end_newline:
                self.add_new_line()
        return self

    def add_links(self):
        if remote_links := self.document_holder.generate_remote_links():
            self.add_label("LINKS")
            self.add(" - ".join(remote_links), escaped=True)
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

    def add_short_abstract(self):
        return (
            self.add_icon()
                .add_title()
                .limits(250, with_dots=True)
                .add_locator()
        )

    def add_view(self, bot_name):
        return (
            self.add_icon(with_cover=True)
                .add_title()
                .limits(400, with_dots=True)
                .add_locator(first_n_authors=3, bot_name=bot_name)
                .add_new_line(2)
                .add_stats()
                .add_links()
                .add_metadata(bot_name=bot_name)
                .add_new_line(2)
                .add_abstract()
                .limits(1500, with_dots=True)
                .add_new_line(2)
                .add_tags(bot_name=bot_name)
                .limits(3000)
        )

    def add_title(self):
        raise NotImplementedError()

    def add_abstract(self):
        raise NotImplementedError()

    def add_locator(self, first_n_authors=1, markup=True, bot_name=None):
        raise NotImplementedError()

    def add_filedata(self, show_filesize=False, with_leading_pipe=False):
        raise NotImplementedError()

    def add_stats(self, end_newline=True):
        return self

    def add_isbns(self, on_newline=False, label=False, end_newline=False):
        if self.document_holder.isbns:
            if on_newline:
                self.add_new_line()
            if label:
                self.add('ISBN:', bold=True)
            self.add(', '.join(self.document_holder.isbns[:2]))
            if end_newline:
                self.add_new_line()
        return self

    def build(self):
        text = ''.join(map(str, self.parts)).strip()
        text = re.sub('\n\n+', '\n\n', text)
        return text


class BaseButtonsBuilder:
    def __init__(self, document_holder, user_language, remote_request_link=None):
        self.document_holder = document_holder
        self.user_language = user_language
        self.remote_request_link = remote_request_link
        self.buttons = [[]]

    def add_back_button(self, back_command):
        self.buttons[-1].append(
            Button.inline(
                text='⬅️',
                data=back_command
            )
        )
        return self

    def add_download_button(self):
        # ⬇️ is a mark, Find+F over sources before replacing
        if not self.document_holder.links:
            return self
        for link in self.document_holder.links:
            label = [link["extension"].upper()]
            if link.get('filesize'):
                label.append(get_formatted_filesize(link["filesize"]))
            self.buttons[-1].append(
                Button.inline(
                    text=f'⬇️ {" | ".join(label)}',
                    data=self.document_holder.get_download_command(link['cid']),
                )
            )
            if len(self.buttons[-1]) > 5:
                self.buttons.append([])
        return self

    def add_remote_download_button(self, bot_name):
        # ⬇️ is a mark, Find+F over sources before replacing
        if self.document_holder.has_field('doi'):
            try:
                encoded_query = encode_query_to_deep_link(f'doi:{self.document_holder.cid}', bot_name)
                self.buttons[-1].append(
                    Button.url('⬇', encoded_query)
                )
            except TooLongQueryError:
                pass
        return self

    def add_remote_request_button(self):
        if self.remote_request_link:
            self.buttons[-1].append(
                Button.url('🙏', self.remote_request_link)
            )
        return self

    def add_close_button(self):
        self.buttons[-1].append(close_button())
        return self

    def add_new_line(self):
        self.buttons.append([])
        return self

    def add_default_layout(self, bot_name, position: int = 0, is_group_mode: bool = False):
        raise NotImplementedError()

    def build(self):
        return self.buttons
