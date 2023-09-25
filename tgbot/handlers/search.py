import asyncio
import re
import time
from abc import ABC
from typing import (
    List,
    Tuple,
)

import grpc.aio
from izihawa_utils.exceptions import NeedRetryError
from telethon import events
from telethon.tl.types import InlineQueryPeerTypeSameBotPM
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
)

from library.telegram.base import RequestContext
from library.telegram.common import close_button
from library.telegram.utils import safe_execution
from library.textutils import DOI_REGEX
from tgbot.app.exceptions import (
    BannedUserError,
    InvalidSearchError,
)
from tgbot.translations import t
from tgbot.views.telegram.base_holder import (
    BaseDocumentHolder,
    BaseTelegramDocumentHolder,
)
from tgbot.views.telegram.common import encode_deep_query
from tgbot.widgets.search_widget import (
    InlineSearchWidget,
    SearchWidget,
)

from .base import (
    BaseCallbackQueryHandler,
    BaseHandler,
    LongTask,
)


def is_doi_query(query: str):
    doi_regex = re.search(DOI_REGEX, query)
    # Fast hack to detect regex queries
    if doi_regex and '*' not in doi_regex.group(2) and '{' not in doi_regex.group(2):
        return doi_regex.group(1) + '/' + doi_regex.group(2)


class RetrieveTask(LongTask):
    def __init__(
        self,
        application,
        request_context,
        document_holder,
        is_upstream,
        ignore_clean_errors,
    ):
        super().__init__(application, request_context, document_holder)
        self.is_upstream = is_upstream
        self.ignore_clean_errors = ignore_clean_errors

    @property
    def task_id(self):
        return self.task_id_for(self.document_holder.get_internal_id())

    @classmethod
    def task_id_for(cls, id_):
        return f'r_{id_}'

    async def long_task(self, request_context: RequestContext):
        return await self.application.file_flow.try_to_download(
            self.document_holder.document,
            is_upstream=self.is_upstream,
            ignore_clean_errors=self.ignore_clean_errors,
        )


class BaseSearchHandler(BaseHandler, ABC):
    @retry(retry=retry_if_exception_type(NeedRetryError), stop=stop_after_attempt(3))
    async def setup_widget(
        self,
        request_context: RequestContext,
        string_query: str,
        is_shortpath_enabled: bool = False,
        load_cache: bool = False,
        store_cache: bool = False,
    ) -> Tuple[str, List, bool]:
        request_context.add_default_fields(
            is_group_mode=request_context.is_group_mode(),
            mode='search',
        )
        start_time = time.time()
        language = request_context.chat['language']
        librarian_service_id = None

        try:
            search_widget = await SearchWidget.create(
                application=self.application,
                request_context=request_context,
                chat=request_context.chat,
                string_query=string_query,
                is_group_mode=request_context.is_group_mode(),
                load_cache=load_cache,
                store_cache=store_cache,
            )
        except InvalidSearchError:
            return t('INVALID_SYNTAX_ERROR', language).format(
                too_difficult_picture_url=self.application.config['application'].get('too_difficult_picture_url', ''),
            ), [close_button()], True
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.ABORTED or e.code() == grpc.StatusCode.UNAVAILABLE:
                return t('MAINTENANCE', language).format(
                    error_picture_url=self.application.config['application'].get('error_picture_url', ''),
                ), [close_button()], True
            else:
                raise

        request_context.statbox(
            action='documents_retrieved',
            duration=time.time() - start_time,
            query=string_query,
            page=0,
            scored_documents=len(search_widget.scored_documents),
        )

        if len(search_widget.scored_documents) == 0:
            if not self.application.metadata_retriever or self.application.is_read_only():
                text, buttons = await search_widget.render(request_context=request_context)
                return text, buttons, False

            doi = is_doi_query(string_query)
            if doi and await self.application.metadata_retriever.try_to_download_metadata({'doi': doi}):
                search_widget = await SearchWidget.create(
                    application=self.application,
                    request_context=request_context,
                    chat=request_context.chat,
                    string_query=string_query,
                    is_group_mode=request_context.is_group_mode(),
                    load_cache=False,
                    store_cache=store_cache,
                )

        if len(search_widget.scored_documents) == 1:
            holder = BaseTelegramDocumentHolder.create(search_widget.scored_documents[0])
            if not holder.has_field('links') or search_widget.query_traits.skip_ipfs or search_widget.query_traits.is_upstream:
                if self.application.is_read_only() or not self.application.started:
                    text, buttons = await search_widget.render(request_context=request_context)
                    if self.application.is_read_only():
                        text = f'{t("READ_ONLY_WARNING")}\n\n{text}'
                    return text, buttons, False
                if self.application.user_manager.has_task(request_context.chat['chat_id'], RetrieveTask.task_id_for(holder.get_internal_id())):
                    return t("ALREADY_DOWNLOADING", request_context.chat["language"]), [close_button()], False
                if self.application.user_manager.hit_limits(request_context.chat['chat_id']):
                    return t("TOO_MANY_DOWNLOADS", request_context.chat["language"]), [close_button()], False

                if holder.has_field('dois'):
                    old_primary_link = holder.primary_link
                    if file := await RetrieveTask(
                        self.application,
                        request_context,
                        holder,
                        is_upstream=search_widget.query_traits.is_upstream,
                        ignore_clean_errors=True,
                    ).schedule():
                        if old_primary_link:
                            await self.application.database.delete_cached_file(old_primary_link['cid'])
                        search_widget = await SearchWidget.create(
                            application=self.application,
                            request_context=request_context,
                            chat=request_context.chat,
                            string_query=string_query,
                            is_group_mode=request_context.is_group_mode(),
                        )
                        holder = BaseTelegramDocumentHolder.create(search_widget.scored_documents[0])
                        await self.application.get_telegram_client(request_context.bot_name).upload_file(
                            file,
                            cache_key=holder.cid,
                        )
                        if self.application.librarian_service:
                            await self.application.librarian_service.delete_request(holder.get_internal_id())
                    elif self.application.librarian_service:
                        librarian_service_id = await self.application.librarian_service.request(holder)
                elif holder.has_field('internal_iso'):
                    librarian_service_id = await self.application.librarian_service.request(holder)

            if (search_widget.query_traits.skip_telegram_cache or search_widget.query_traits.skip_ipfs) and holder.primary_link:
                request_context.statbox(**{
                    'action': 'omit_cache',
                    'cid': holder.primary_link['cid'],
                })
                await self.application.database.delete_cached_file(holder.cid)

            if is_shortpath_enabled:
                view = holder.view_builder(language).add_new_line(2).add_view(bot_name=request_context.bot_name).build()
                remote_request_link = None
                if librarian_service_id:
                    remote_request_link = f'https://t.me/{self.application.librarian_service.group_name}/{librarian_service_id}'
                buttons = holder.buttons_builder(language, remote_request_link).add_default_layout(
                    bot_name=request_context.bot_name,
                    position=0,
                    is_group_mode=request_context.is_group_mode(),
                ).build()
                return view, buttons, holder.has_cover()

        view, buttons = await search_widget.render(request_context=request_context)
        return view, buttons, False


class SearchHandler(BaseSearchHandler):
    filter = events.NewMessage(incoming=True, pattern=re.compile(r'^(/search(?:@\w+)?\s+)?(.*)', flags=re.DOTALL))
    is_group_handler = True

    def check_search_ban_timeout(self, user_id: str):
        ban_timeout = self.application.user_manager.check_search_ban_timeout(user_id=user_id)
        if ban_timeout:
            raise BannedUserError(ban_timeout=ban_timeout)
        self.application.user_manager.add_search_time(user_id=user_id, search_time=time.time())

    def parse_pattern(self, event: events.ChatAction):
        search_prefix = event.pattern_match.group(1)
        query = event.pattern_match.group(2).strip()
        return search_prefix, query

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        language = request_context.chat['language']
        try:
            self.check_search_ban_timeout(user_id=str(request_context.chat['chat_id']))
        except BannedUserError as e:
            request_context.error_log(e)
            async with safe_execution(error_log=request_context.error_log):
                return await event.reply(t('BANNED_FOR_SECONDS', language).format(
                    seconds=e.ban_timeout,
                    reason=t('BAN_MESSAGE_TOO_MANY_REQUESTS', language),
                ))
        search_prefix, string_query = self.parse_pattern(event)

        if request_context.is_group_mode() and not search_prefix:
            return
        if request_context.is_personal_mode() and search_prefix:
            string_query = event.raw_text

        prefetch_message = await event.reply(
            t("SEARCHING", language),
        )
        try:
            text, buttons, link_preview = await self.setup_widget(
                request_context=request_context,
                string_query=string_query,
                is_shortpath_enabled=True,
                load_cache=False,
                store_cache=True,
            )
            if self.extra_warning:
                text = self.extra_warning + text
            return await self.application.get_telegram_client(request_context.bot_name).edit_message(
                request_context.chat['chat_id'],
                prefetch_message.id,
                text,
                buttons=buttons,
                link_preview=link_preview,
            )
        except asyncio.CancelledError as e:
            await asyncio.gather(prefetch_message.delete(), event.delete())
            raise e
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.ABORTED or e.code() == grpc.StatusCode.UNAVAILABLE:
                await asyncio.gather(prefetch_message.delete(), event.delete())
            raise e


class InlineSearchHandler(BaseSearchHandler):
    filter = events.InlineQuery()
    stop_propagation = False

    async def handler(self, event: events.InlineQuery, request_context: RequestContext):
        if event.query.peer_type == InlineQueryPeerTypeSameBotPM():
            await event.answer()
            return

        builder = event.builder

        try:
            if len(event.text) <= 3:
                await event.answer([])
                raise events.StopPropagation()

            inline_search_widget = await InlineSearchWidget.create(
                application=self.application,
                request_context=request_context,
                chat=request_context.chat,
                string_query=event.text,
                is_group_mode=request_context.is_group_mode(),
                load_cache=True,
            )
            items = inline_search_widget.render(builder=builder, request_context=request_context)
            encoded_query = encode_deep_query(event.text)
            if len(encoded_query) < 32:
                await event.answer(
                    items,
                    private=True,
                    switch_pm=request_context.bot_name,
                    switch_pm_param=encoded_query,
                )
            else:
                await event.answer(items)
        except InvalidSearchError:
            await event.answer([])
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.ABORTED or e.code() == grpc.StatusCode.UNAVAILABLE:
                await event.answer([])
            else:
                raise
        raise events.StopPropagation()


class SearchEditHandler(BaseSearchHandler):
    filter = events.MessageEdited(incoming=True, pattern=re.compile(r'^(/search(?:@\w+)\s+)?(.*)', flags=re.DOTALL))
    is_group_handler = True

    def parse_pattern(self, event: events.ChatAction):
        search_prefix = event.pattern_match.group(1)
        query = event.pattern_match.group(2).strip()
        return search_prefix, query

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        search_prefix, string_query = self.parse_pattern(event)
        request_context.add_default_fields(mode='search_edit')

        if request_context.is_group_mode() and not search_prefix:
            return

        if request_context.is_personal_mode() and search_prefix:
            string_query = event.raw_text

        for next_message in await self.get_last_messages_in_chat(event, request_context=request_context):
            if next_message.is_reply and event.id == next_message.reply_to_msg_id:
                request_context.statbox(action='resolved')
                text, buttons, link_preview = await self.setup_widget(
                    request_context=request_context,
                    string_query=string_query,
                    is_shortpath_enabled=True,
                    store_cache=True,
                )
                if self.extra_warning:
                    text = self.extra_warning + text
                return await self.application.get_telegram_client(request_context.bot_name).edit_message(
                    request_context.chat['chat_id'],
                    next_message.id,
                    text,
                    buttons=buttons,
                    link_preview=link_preview,
                )
        return await event.reply(
            t('REPLY_MESSAGE_HAS_BEEN_DELETED', request_context.chat['language']),
        )


class SearchPagingHandler(BaseCallbackQueryHandler):
    filter = events.CallbackQuery(pattern='^/search_([0-9]+)$')

    def parse_pattern(self, event: events.ChatAction):
        page = int(event.pattern_match.group(1).decode())
        return page

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        page = self.parse_pattern(event)
        request_context.add_default_fields(mode='search_paging')
        message = await event.get_message()

        if not message:
            return await event.answer()

        reply_message = await message.get_reply_message()
        if not reply_message:
            return await event.respond(
                t('REPLY_MESSAGE_HAS_BEEN_DELETED', request_context.chat['language']),
            )

        string_query = reply_message.raw_text.replace(f'@{request_context.bot_name}', '').strip()

        try:
            search_widget = await SearchWidget.create(
                application=self.application,
                request_context=request_context,
                chat=request_context.chat,
                string_query=string_query,
                page=page,
                load_cache=True,
                store_cache=True,
            )
        except InvalidSearchError:
            return await event.answer(
                t('MAINTENANCE_WO_PIC', request_context.chat['language']),
            )
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.ABORTED or e.code() == grpc.StatusCode.UNAVAILABLE:
                await event.answer([])
                return
            else:
                raise

        request_context.statbox(
            action='documents_retrieved',
            query=string_query,
            page=page,
            scored_documents=len(search_widget.scored_documents),
        )

        serp, buttons = await search_widget.render(request_context=request_context)
        await message.edit(serp, buttons=buttons, link_preview=False)
        async with safe_execution(is_logging_enabled=False):
            await event.answer()
