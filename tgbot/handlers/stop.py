from telethon import events

from library.telegram.base import RequestContext

from .base import BaseHandler


class StopHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern='^/stop$')

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        request_context.statbox(action='show', mode='stop')
