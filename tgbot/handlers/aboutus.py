from telethon import Button, events

from library.telegram.base import RequestContext
from tgbot.translations import t

from .base import BaseHandler


class AboutusHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern='^/aboutus(@[A-Za-z0-9_]+)?$')
    is_group_handler = True

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        request_context.statbox(action='show', mode='aboutus')
        await event.reply(
            t('ABOUT_US', request_context.chat['language']),
            buttons=Button.clear(),
            link_preview=False,
        )
