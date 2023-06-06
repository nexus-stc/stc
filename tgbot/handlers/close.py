import asyncio
import time

from telethon import events

from library.telegram.base import RequestContext
from library.telegram.utils import safe_execution
from tgbot.translations import t

from .base import BaseCallbackQueryHandler


def is_earlier_than_2_days(message):
    if message.date:
        return time.time() - time.mktime(message.date.timetuple()) < 48 * 60 * 60 - 10


class CloseHandler(BaseCallbackQueryHandler):
    filter = events.CallbackQuery(pattern='^/close(?:_([A-Za-z0-9]+))?(?:_([0-9]+))?$')

    async def handler(self, event, request_context: RequestContext):
        session_id = event.pattern_match.group(1)
        if session_id:
            session_id = session_id.decode()
        request_context.add_default_fields(mode='close')

        target_events = []
        message = await event.get_message()

        if message and is_earlier_than_2_days(message):
            target_events.append(event.answer())
            request_context.statbox(
                action='close',
                message_id=message.id,
                session_id=session_id,
            )
            reply_message = await message.get_reply_message()
            if reply_message and is_earlier_than_2_days(reply_message):
                target_events.append(reply_message.delete())
            target_events.append(message.delete())
        else:
            async with safe_execution(is_logging_enabled=False):
                await event.answer(t('DELETION_FORBIDDEN_DUE_TO_AGE'))
        await asyncio.gather(*target_events)
