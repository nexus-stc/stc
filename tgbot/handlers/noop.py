from telethon import events

from library.telegram.base import RequestContext

from .base import BaseCallbackQueryHandler


class NoopHandler(BaseCallbackQueryHandler):
    filter = events.CallbackQuery(pattern='^/noop$')

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        request_context.statbox(action='start', mode='noop')
        await event.answer()
