import re

from telethon import events

from library.telegram.base import RequestContext

from .base import BaseHandler


class LibrarianTextHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern=re.compile(r'(.*)', flags=re.DOTALL))
    is_group_handler = True

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        session_id = self.generate_session_id()
        request_context.add_default_fields(mode='librarian_text', session_id=session_id)
        user_id = event.sender_id

        if user_id not in self.application.config['librarian']['moderators']:
            await event.delete()
