import asyncio
import re
from urllib.parse import unquote

from telethon import events

from library.telegram.base import RequestContext
from library.telegram.common import close_button
from library.textutils import DOI_REGEX
from tgbot.app.exceptions import UnknownFileFormatError
from tgbot.translations import t

from ..app.librarian_service import extract_internal_id
from .base import BaseHandler


def is_submit_message(event):
    if event.document and event.document.mime_type in ('application/octet-stream', 'application/pdf', 'application/zip'):
        return True
    if event.fwd_from and event.fwd_from.document and event.document.mime_type in (
        'application/octet-stream', 'application/pdf', 'application/zip'
    ):
        return True
    return False


class SubmitHandler(BaseHandler):
    filter = events.NewMessage(func=is_submit_message, incoming=True)
    is_group_handler = True
    writing_handler = True

    def get_internal_id_hint(self, message, reply_message) -> str:
        internal_id_hint = None
        if message.text:
            if internal_id := extract_internal_id(message.text):
                return internal_id
            elif doi_regex := re.search(DOI_REGEX, message.raw_text):
                internal_id_hint = 'id.dois:' + doi_regex.group(1) + '/' + doi_regex.group(2)
        if not internal_id_hint and reply_message:
            if internal_id := extract_internal_id(reply_message.text):
                return internal_id
            elif doi_regex := re.search(DOI_REGEX, reply_message.raw_text):
                internal_id_hint = 'id.dois:' + doi_regex.group(1) + '/' + doi_regex.group(2)
        return internal_id_hint

    async def handler(self, event, request_context: RequestContext):
        session_id = self.generate_session_id()

        request_context.add_default_fields(session_id=session_id)
        request_context.statbox(action='show', mode='submit', mime_type=event.document.mime_type)

        reply_message = await event.get_reply_message()
        internal_id_hint = self.get_internal_id_hint(message=event, reply_message=reply_message)
        request_context.statbox(action='doi_hint', internal_id_hint=internal_id_hint)

        if not internal_id_hint:
            return await event.reply(
                t('NO_DOI_HINT', request_context.chat['language']),
                buttons=None if request_context.is_group_mode() else [close_button()],
            )
        field, value = internal_id_hint.split(':', 1)

        match event.document.mime_type:
            case 'application/pdf':
                if self.application.librarian_service:
                    document = await self.application.summa_client.get_one_by_field_value(
                        'nexus_science',
                        field,
                        value,
                    )
                    uploaded_message = await self.application.librarian_service.process_file(
                        event,
                        request_context,
                        document,
                    )
                    await self.application.database.add_upload(event.sender_id, uploaded_message.id, internal_id_hint)
            case _:
                request_context.statbox(action='unknown_file_format')
                request_context.error_log(UnknownFileFormatError(format=event.document.mime_type))
                return await asyncio.gather(
                    event.reply(
                        t('UNKNOWN_FILE_FORMAT_ERROR', request_context.chat['language']),
                        buttons=None if request_context.is_group_mode() else [close_button()],
                    ),
                    event.delete(),
                )
