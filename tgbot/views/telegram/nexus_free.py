from typing import Optional

from .base_view_builder import BaseButtonsBuilder, BaseViewBuilder


class NexusFreeButtonsBuilder(BaseButtonsBuilder):
    def add_default_layout(self, bot_name, position: int = 0, is_group_mode: bool = False):
        if is_group_mode:
            return (
                self.add_remote_download_button(bot_name)
                .add_close_button()
            )
        else:
            return (
                self.add_download_button()
                    .add_close_button()
            )


class NexusFreeViewBuilder(BaseViewBuilder):
    def add_edition(self, with_brackets=True, bold=False):
        edition = self.document_holder.edition
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

    def add_pages(self):
        if self.document_holder.pages:
            self.add(f'pp. {self.document_holder.pages}')
        return self

    def add_title(self, bold=True):
        title = self.document_holder.title or ''
        if self.document_holder.iso_id:
            title = f'{self.document_holder.iso_id.upper()} - {title}'
        elif self.document_holder.bs_id:
            title = f'{self.document_holder.bs_id.upper()} - {title}'
        if self.document_holder.periodical:
            if title:
                title += f' ({self.document_holder.periodical})'
            else:
                title += self.document_holder.periodical
        elif self.document_holder.volume:
            if title:
                title += f' ({self.document_holder.volume})'
            else:
                title += self.document_holder.volume
        self.add(title, bold=bold)
        self.add_edition(with_brackets=True, bold=bold)
        return self

    def add_locator(self, first_n_authors=1, markup=True, bot_name=None):
        return (
            self.add_authors(first_n_authors=first_n_authors, on_newline=True, bot_name=None)
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

    def add_abstract(self, limit: Optional[int] = None):
        if self.document_holder.abstract:
            self.add(self.document_holder.abstract)
        return self
