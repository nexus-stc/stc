import asyncio
import time

from telethon import (
    events,
    functions,
)
from telethon.errors import MessageIdInvalidError

from library.telegram.base import RequestContext
from tgbot.translations import t
from tgbot.views.telegram.base_holder import BaseHolder

from .base import BaseHandler


def is_earlier_than_2_days(message):
    if message.date:
        return time.time() - time.mktime(message.date.timetuple()) < 2 * 24 * 60 * 60 - 10


class ViewHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern='^/v_([A-Za-z0-9_-]+)')

    def parse_pattern(self, event: events.ChatAction):
        cid = event.pattern_match.group(1)
        return cid

    async def get_message(self, message_id, request_context: RequestContext):
        get_message_request = functions.messages.GetMessagesRequest(id=[message_id])
        messages = await self.application.get_telegram_client(request_context.bot_name)(get_message_request)
        return messages.messages[0]

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        cid = self.parse_pattern(event)

        request_context.add_default_fields(mode='view', cid=cid)
        request_context.statbox(action='view')

        language = request_context.chat['language']

        try:
            prefetch_message = await event.reply(t("SEARCHING", request_context.chat['language']))
            scored_document = await self.get_scored_document(
                self.bot_index_aliases,
                'cid',
                cid,
            )
            if not scored_document:
                return await event.reply(t("OUTDATED_VIEW_LINK", language))
            holder = BaseHolder.create(scored_document)
            promo = self.application.promotioner.choose_promotion(language)
            view_builder = holder.view_builder(language).add_view(bot_name=request_context.bot_name).add_new_line(2).add(promo, escaped=True)
            buttons = holder.buttons_builder(language).add_default_layout(
                bot_name=request_context.bot_name,
                is_group_mode=request_context.is_group_mode(),
            ).build()
            return await asyncio.gather(
                event.delete(),
                prefetch_message.edit(view_builder.build(), buttons=buttons, link_preview=holder.has_cover()),
            )
        except MessageIdInvalidError:
            return await event.reply(t("VIEWS_CANNOT_BE_SHARED", language))
