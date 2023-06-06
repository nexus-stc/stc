from telethon import Button

from library.telegram.base import RequestContext
from library.telegram.common import close_button
from tgbot.app.application import TelegramApplication
from tgbot.translations import t
from tgbot.views.telegram.base_holder import BaseHolder
from tgbot.views.telegram.common import TooLongQueryError, encode_query_to_deep_link


class BaseSearchWidget:
    """
    Presents markup for the SERP.
    """

    query_tags = ['search']

    def __init__(
        self,
        application: TelegramApplication,
        request_context: RequestContext,
        chat: dict,
        query: str,
        index_aliases,
        page: int = 0,
        is_group_mode: bool = False,
    ):
        self.application = application
        self.request_context = request_context
        self.chat = chat
        self.query = query
        self.index_aliases = index_aliases
        self.page = page
        self.is_group_mode = is_group_mode

    @classmethod
    async def create(
        cls,
        application: TelegramApplication,
        request_context: RequestContext,
        chat: dict,
        query: str,
        index_aliases,
        page: int = 0,
        is_group_mode: bool = False,
    ):
        search_widget_view = cls(
            application=application,
            request_context=request_context,
            chat=chat,
            query=query,
            index_aliases=index_aliases,
            page=page,
            is_group_mode=is_group_mode,
        )
        await search_widget_view._acquire_documents()
        return search_widget_view

    async def _acquire_documents(self):
        queries = self.application.query_processor.process(
            self.query,
            page=self.page,
            page_size=self.application.config['application']['page_size'],
            index_aliases=self.index_aliases
        )
        self._search_response = await self.application.summa_client.search(queries)

    @property
    def count(self) -> int:
        return self._search_response.collector_outputs[1].count.count

    @property
    def has_next(self) -> bool:
        return self._search_response.collector_outputs[0].documents.has_next

    @property
    def scored_documents(self) -> list:
        return self._search_response.collector_outputs[0].documents.scored_documents


class SearchWidget(BaseSearchWidget):
    async def render(self, message_id, request_context: RequestContext) -> tuple:
        if len(self.scored_documents) == 0:
            return t('COULD_NOT_FIND_ANYTHING', self.chat['language']), [close_button()]

        serp_elements = []

        for scored_document in self.scored_documents:
            holder = BaseHolder.create(scored_document, scored_document.snippets)

            el = (
                holder
                .view_builder(self.chat['language'])
                .add_short_abstract()
                .add_snippet()
                .add_new_line()
            )
            need_pipe = False
            if holder.has_field('cid'):
                if self.is_group_mode:
                    el = el.add(holder.get_ipfs_gateway_link(), escaped=True)
                else:
                    el = el.add(holder.get_view_command())
                need_pipe = True
            elif holder.has_field('doi') and not self.is_group_mode:
                try:
                    deep_link = encode_query_to_deep_link('🔬 ' + holder.doi, request_context.bot_name)
                    if not self.application.is_read_only() and self.application.librarian_service:
                        el = el.add(f'[request]({deep_link})', escaped=True)
                        need_pipe = True
                except TooLongQueryError:
                    pass
            el = (
                el
                .add_doi_link(with_leading_pipe=need_pipe, text='doi.org')
                .add_references_counter(bot_name=request_context.bot_name, with_leading_pipe=True)
                .add_filedata(show_filesize=True, with_leading_pipe=True)
                .build()
            )

            serp_elements.append(el)

        serp_elements.append(f"__{t('FOUND_N_ITEMS', self.chat['language']).format(count=self.count)}__")
        serp = '\n\n'.join(serp_elements)

        if self.is_group_mode:
            try:
                encoded_query = encode_query_to_deep_link(
                    self.query,
                    request_context.bot_name,
                )
                serp = (
                    f"{serp}\n\n**{t('DOWNLOAD_AND_SEARCH_MORE', self.chat['language'])}: **"
                    f'[@{request_context.bot_name}]'
                    f'({encoded_query})'
                )
            except TooLongQueryError:
                serp = (
                    f"{serp}\n\n**{t('DOWNLOAD_AND_SEARCH_MORE', self.chat['language'])}: **"
                    f'[@{request_context.bot_name}]'
                    f'(https://t.me/{request_context.bot_name})'
                )
        promotion_language = self.chat['language']
        promo = self.application.promotioner.choose_promotion(promotion_language)
        serp = f'{serp}\n\n{promo}\n'

        buttons = None
        if not self.is_group_mode:
            buttons = []
            if self.has_next or self.page > 0:
                buttons = [
                    Button.inline(
                        text='<<1' if self.page > 1 else ' ',
                        data='/search_0' if self.page > 1 else '/noop',
                    ),
                    Button.inline(
                        text=f'<{self.page}' if self.page > 0 else ' ',
                        data=f'/search_{self.page - 1}'
                        if self.page > 0 else '/noop',
                    ),
                    Button.inline(
                        text=f'{self.page + 2}>' if self.has_next else ' ',
                        data=f'/search_{self.page + 1}'
                        if self.has_next else '/noop',
                    )
                ]
            buttons.append(close_button())
        return serp, buttons


class InlineSearchWidget(BaseSearchWidget):
    query_tags = ['inline_search']

    def render(self, builder, request_context: RequestContext) -> list:
        items = []

        for scored_document in self.scored_documents:
            holder = BaseHolder.create(scored_document)
            title = holder.view_builder(self.chat['language']).add_icon().add_title(bold=False).limits(140).build()
            abstract = (
                holder.view_builder(self.chat['language'])
                .add_filedata(show_filesize=False).add_new_line().add_locator(markup=False).limits(160).build()
            )
            response_text = holder.view_builder(self.chat['language']).add_short_abstract().build()
            buttons = holder.buttons_builder(self.chat['language']).add_remote_download_button(bot_name=request_context.bot_name).build()
            items.append(builder.article(
                title,
                id=str(holder.id),
                text=response_text,
                abstract=abstract,
                buttons=buttons,
            ))

        return items
