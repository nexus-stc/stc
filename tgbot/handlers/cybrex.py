import re

from telethon import events

from library.telegram.base import RequestContext

from .base import BaseHandler


class CybrexHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern=re.compile(r'^/cybrex(?:@\w+)?(.*)?$', re.DOTALL))
    is_group_handler = True

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        session_id = self.generate_session_id()
        request_context.add_default_fields(mode='cybrex', session_id=session_id)
        request_context.statbox(action='show')
        is_allowed = (
            int(request_context.chat['chat_id']) in self.application.config['application']['cybrex_whitelist']
            or (event.from_id is not None and int(event.from_id.user_id) in self.application.config['application']['cybrex_whitelist'])
        )
        if not is_allowed:
            return await event.reply('Only People of Nexus can ask me')

        query = event.pattern_match.group(1).strip()

        n_summa_documents = 3
        if 'OFFLINE' in query:
            query = query.replace('OFFLINE', '')
            n_summa_documents = 0

        wait_message = await event.reply('`Looking for the answer in STC (2-3 minutes)...`')
        answer, documents, summa_documents = await self.application.cybrex_ai.chat_science(
            query=query,
            n_results=3,
            n_summa_documents=n_summa_documents,
        )

        short_snippets = [
            f' - `{summa_document["doi"]}`: {summa_document["title"]}'
            for summa_document in summa_documents
        ]
        short_sources = '\n'.join(short_snippets)
        response = f'**{query}**\n🤖: {answer}\n\n**References:**\n{short_sources}'
        await event.reply(response)

        full_snippets = [
            f' - `{document["metadata"]["doi"]}`: {document["text"]}'
            for document in documents
        ]
        sources = '\n'.join(full_snippets)
        sources = f'**Text snippets:**\n{sources}'
        await event.reply(sources)
        await wait_message.delete()
