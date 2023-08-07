from telethon import events

from library.telegram.base import RequestContext
from tgbot.translations import t
from tgbot.views.telegram.common import (
    TooLongQueryError,
    encode_query_to_deep_link,
)

from .base import BaseHandler


class ShortlinkHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern='^/shortlink\\s?(.*)?')

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        query = event.pattern_match.group(1)
        request_context.statbox(action='start', mode='shortlink', query=query)

        try:
            text = encode_query_to_deep_link(query, request_context.bot_name)
        except TooLongQueryError:
            text = t('TOO_LONG_QUERY_FOR_SHORTLINK', request_context.chat['language'])

        return await event.reply(f'`{text}`', link_preview=False)
