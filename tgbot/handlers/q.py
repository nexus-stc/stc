import asyncio
import re

from bs4 import BeautifulSoup
from telethon import events

from library.telegram.base import RequestContext
from library.telegram.common import close_button
from library.textutils.utils import remove_markdown

from ..translations import t
from .base import BaseHandler
from ..views.telegram.common import encode_query_to_deep_link


class QHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern=re.compile(r'^/q(?:@\w+)?(?:\s+(.*))?$', re.DOTALL))
    is_group_handler = True

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        session_id = self.generate_session_id()
        request_context.add_default_fields(mode='cybrex', session_id=session_id)
        request_context.statbox(action='show', sender_id=event.sender_id)

        query = event.pattern_match.group(1)
        if not query:
            text = "Send query for semantic search after `/q`: `/q What is hemoglobin?`"
            return await event.reply(text)
        query = query.strip()

        scored_chunks = await self.application.cybrex_ai.semantic_search(query, n_chunks=3, n_documents=0)
        response = f'🤔 **{query}**'

        references = []
        for scored_chunk in scored_chunks[:3]:
            field, value = scored_chunk.chunk.document_id.split(':', 2)

            document_id = f'{field}:{value}'
            title = scored_chunk.chunk.title.replace('\n', ' - ')
            text_title = BeautifulSoup(title or '', 'lxml').get_text(separator='')
            deep_query = encode_query_to_deep_link(document_id, bot_name=request_context.bot_name)
            if deep_query:
                reference = f' - **{text_title}** - [{document_id}]({deep_query})'
            else:
                reference = f' - **{text_title}** - `{document_id}`'
            reference += f'\n**Text:** {remove_markdown(scored_chunk.chunk.text)}'
            references.append(reference)

        references = '\n\n'.join(references)
        if references:
            response += f'\n\n**References:**\n\n{references}'
        return await event.reply(response, buttons=[close_button()])
