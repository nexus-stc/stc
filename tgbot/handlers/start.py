import asyncio

from telethon import events

from library.telegram.base import RequestContext
from tgbot.translations import t
from tgbot.views.telegram.common import (
    DecodeDeepQueryError,
    decode_deep_query, recode_base64_to_base36,
)

from .search import BaseSearchHandler


class StartHandler(BaseSearchHandler):
    filter = events.NewMessage(incoming=True, pattern='^/start\\s?(.*)?')

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        raw_query = event.pattern_match.group(1)
        string_query = None

        request_context.statbox(action='start', mode='start', text=event.text)

        try:
            string_query = decode_deep_query(raw_query)
        except DecodeDeepQueryError as e1:
            try:
                cid = recode_base64_to_base36(raw_query)
                string_query = f'links.cid:{cid}'
            except DecodeDeepQueryError as e2:
                request_context.error_log(e1, mode='start', raw_query=raw_query)
                request_context.error_log(e2, mode='start', raw_query=raw_query)

        if string_query:
            request_context.statbox(action='query', mode='start', query=string_query)
            request_message = await self.application.get_telegram_client(request_context.bot_name).send_message(event.chat, string_query)
            prefetch_message = await request_message.reply(
                t("SEARCHING", request_context.chat['language']),
            )
            try:
                text, buttons, link_preview = await self.setup_widget(
                    request_context=request_context,
                    string_query=string_query,
                    is_shortpath_enabled=True,
                )
                edit_action = self.application.get_telegram_client(request_context.bot_name).edit_message(
                    request_context.chat['chat_id'],
                    prefetch_message.id,
                    text,
                    buttons=buttons,
                    link_preview=link_preview,
                )
                await asyncio.gather(
                    event.delete(),
                    edit_action,
                )
            except Exception:
                await prefetch_message.delete()
                raise
        else:
            request_context.statbox(action='show', mode='start')
            await event.reply(t('HELP', request_context.chat['language']))
