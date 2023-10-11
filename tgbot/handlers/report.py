import asyncio

from stc_geck.advices import BaseDocumentHolder
from telethon import events

from library.telegram.base import RequestContext
from library.telegram.utils import safe_execution

from .base import BaseCallbackQueryHandler


class ReportHandler(BaseCallbackQueryHandler):
    filter = events.NewMessage(incoming=True, pattern=r'^(?:@\w+)?\s+\/r_([A-Za-z0-9_-]+)$')

    def parse_pattern(self, event: events.ChatAction):
        cid = event.pattern_match.group(1)
        return cid

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        cid = self.parse_pattern(event)

        request_context.add_default_fields(mode='report', cid=cid)
        request_context.statbox(action='report')

        document = await self.application.summa_client.get_one_by_field_value('nexus_science', 'cid', cid)
        document_holder = BaseDocumentHolder(document)

        await self.application.database.add_vote_broken_file(
            bot_name=self.bot_config['bot_name'],
            user_id=request_context.chat['chat_id'],
            internal_id=document_holder.get_internal_id(),
            cid=cid,
        )
        async with safe_execution():
            return await asyncio.gather(
                event.reply(
                    f'Thank you for reporting `{document_holder.get_internal_id()}`. '
                    f'Be careful, too many misreports will cause a ban',
                ),
                event.delete(),
            )
