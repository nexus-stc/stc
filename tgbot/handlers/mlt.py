import json

from izihawa_utils.common import filter_none
from telethon import (
    events,
)

from library.telegram.base import RequestContext
from library.telegram.common import close_button
from tgbot.translations import t
from tgbot.views.telegram.base_holder import BaseTelegramDocumentHolder

from ..views.telegram.common import (
    recode_base64_to_base36,
    remove_button,
)
from .base import BaseHandler


class MltHandler(BaseHandler):
    filter = events.CallbackQuery(pattern='^/m_([A-Za-z0-9_-]+)')

    def parse_pattern(self, event: events.ChatAction):
        cid = recode_base64_to_base36(event.pattern_match.group(1).decode())
        return cid

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        cid = self.parse_pattern(event)

        request_context.add_default_fields(mode='mlt', cid=cid)
        request_context.statbox(action='view')

        prefetch_message = await event.reply(t("SEARCHING", request_context.chat['language']))
        source_document = await self.application.summa_client.get_one_by_field_value('nexus_science', 'links.cid', cid)

        if not source_document:
            return await event.reply(t("OUTDATED_VIEW_LINK", request_context.chat['language']))

        document_dump = filter_none({
            'title': source_document.get('title'),
            'abstract': source_document.get('abstract'),
            'tags': source_document.get('tags'),
            'languages': source_document.get('languages'),
        })

        requested_type = 'type:book type:edited-book type:monograph type:reference-book'
        if source_document['type'] == 'journal-article':
            requested_type += ' type:journal-article'

        documents = await self.application.summa_client.search_documents({
            'index_alias': 'nexus_science',
            'query': {'boolean': {'subqueries': [{
                'occur': 'must',
                'query': {'more_like_this': {
                    'min_term_frequency': 1,
                    'min_doc_frequency': 1,
                    'document': json.dumps(document_dump)
                }}
            }, {
                'occur': 'must',
                'query': {'match': {
                    'value': requested_type,
                }}
            }]}},
            'collectors': [{'top_docs': {'limit': 5}}],
        })

        serp_elements = []
        for document in documents:
            serp_elements.append(BaseTelegramDocumentHolder(document).base_render(
                request_context,
                with_librarian_service=bool(self.application.librarian_service) and not self.application.is_read_only()
            ))
        serp = '\n\n'.join(serp_elements)
        serp = f'**Similar To: {source_document.get("title")}**\n\n{serp}'
        await remove_button(event, '🖲', and_empty_too=True)
        return await prefetch_message.edit(serp, buttons=[close_button()])
