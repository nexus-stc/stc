import re

from telethon import events

from library.telegram.base import RequestContext

from .base import BaseHandler


class QHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern=re.compile(r'^/q(?:@\w+)?\s+(.*)?$', re.DOTALL))
    is_group_handler = True

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        session_id = self.generate_session_id()
        request_context.add_default_fields(mode='cybrex', session_id=session_id)
        request_context.statbox(action='show', sender_id=event.sender_id, event=str(event))

        query = event.pattern_match.group(1).strip()
        if not query:
            text = "Post your query statement for semantic search after /q: `/q What is hemoglobin?"
            return await event.reply(text)

        chunks = await self.application.cybrex_ai.semantic_search(query, n_chunks=3, n_documents=0)
        response = f'🤔 **{query}**'

        references = []
        for chunk in chunks[:3]:
            index_alias, field, value = chunk['document_id'].split(':', 2)
            document_id = f'{field}:{value}'
            reference = f' - **{chunk["title"]}** - `{document_id}`'
            reference += f'\n**Text:** {chunk["text"]}'
            references.append(reference)

        references = '\n\n'.join(references)
        if references:
            response += f'\n\n**References:**\n\n{references}'

        await event.reply(response)
