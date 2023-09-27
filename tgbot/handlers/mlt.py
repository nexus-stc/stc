import json

from izihawa_utils.common import filter_none
from telethon import events

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
    filter = events.CallbackQuery(pattern='^/(m|n)_(.*)')
    fail_as_reply = False

    def parse_pattern(self, event: events.ChatAction):
        command = event.pattern_match.group(1).decode()
        if command == 'm':
            cid = recode_base64_to_base36(event.pattern_match.group(2).decode())
            return 'links.cid', cid
        else:
            internal_id = event.pattern_match.group(2).decode()
            return internal_id.split(':', 1)

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        field, value = self.parse_pattern(event)

        request_context.add_default_fields(mode='mlt', field=field, value=value)
        request_context.statbox(action='view')

        prefetch_message = await self.application.get_telegram_client(request_context.bot_name).send_message(
            event.chat,
            t("SEARCHING", request_context.chat['language'])
        )

        source_document = await self.application.summa_client.get_one_by_field_value('nexus_science', field, value)

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

        subqueries = [{
            'occur': 'should',
            'query': {'more_like_this': {
                'min_term_frequency': 1,
                'min_doc_frequency': 1,
                'document': json.dumps(document_dump)
            }}
        }]

        if content := source_document.get('content'):
            subqueries.append({
                'occur': 'should',
                'query': {
                    'boost': {
                        'query': {
                            'more_like_this': {
                                'min_term_frequency': 3,
                                'min_doc_frequency': 1,
                                'document': json.dumps({'content': content})
                            }
                        },
                        'score': '0.35',
                    }
                }
            })

        documents = await self.application.summa_client.search_documents({
            'index_alias': 'nexus_science',
            'query': {'boolean': {'subqueries': [
                {'occur': 'must', 'query': {'boolean': {'subqueries': subqueries}}},
                {'occur': 'must', 'query': {'match': {'value': requested_type}}}
            ]}},
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
