from telethon import events

from library.telegram.base import RequestContext
from tgbot.configs import config
from tgbot.translations import t

from .base import BaseHandler


class HowToHelpHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern='^/howtohelp(@[A-Za-z0-9_]+)?$')
    is_group_handler = True

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        request_context.statbox(action='show', mode='howtohelp')
        await event.reply(
            t('HOW_TO_HELP', request_context.chat['language']).format(
                related_channel=config['telegram'].get('related_channel', '🚫'),
                twitter_contact_url=config['twitter'].get('contact_url', '🚫')
            ))
