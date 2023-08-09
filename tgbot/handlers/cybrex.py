import re

from telethon import events

from library.telegram.base import RequestContext

from .base import BaseHandler


class CybrexHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern=re.compile(r'^/cybrex(?:@\w+)?\s+(.*)?$', re.DOTALL))
    is_group_handler = True

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        session_id = self.generate_session_id()
        request_context.add_default_fields(mode='cybrex', session_id=session_id)
        request_context.statbox(action='show', requestor=str(event), sender_id=event.sender_id)
        is_allowed = int(event.sender_id) in self.application.config['application']['cybrex_whitelist']
        if not is_allowed:
            return await event.reply('Only People of Nexus can call me')

        query = event.pattern_match.group(1).strip()
        if not query:
            text = "My name is Cybrex and I can respond queries based on STC data."
            return await event.reply(text)

        n_documents = 0
        if '--online' in query:
            query = query.replace('--online', '').strip()
            n_documents = 5

        wait_message = await event.reply('`Looking for the answer in STC (2-3 minutes)...`')
        answer, documents, summa_documents = await self.application.cybrex_ai.chat_science(
            query=query,
            n_chunks=5,
            n_documents=n_documents,
        )
        response = f'**{query}**\n🤖: {answer}'
        request_context.statbox(
            action='queried_documents',
            documents=documents,
        )
        short_snippets = [
            f' - `{summa_document["doi"]}`: {summa_document["title"]}'
            for summa_document in summa_documents
        ]
        short_sources = '\n'.join(short_snippets)
        if short_sources:
            response += f'\n\n**References:**\n{short_sources}'
        await event.reply(response)
        await wait_message.delete()


class CybrexDocHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern=re.compile(r'^/cybrex_doc(?:@\w+)?\s+(.*)?$', re.DOTALL))
    is_group_handler = True

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        session_id = self.generate_session_id()
        request_context.add_default_fields(mode='cybrex_doc', session_id=session_id)
        request_context.statbox(action='show', requestor=str(event), sender_id=event.sender_id)
        is_allowed = int(event.sender_id) in self.application.config['application']['cybrex_whitelist']
        if not is_allowed:
            return await event.reply('Only People of Nexus can call me')

        query = event.pattern_match.group(1).strip()
        if not query:
            text = "My name is Cybrex and I can respond queries based on STC data."
            return await event.reply(text)

        wait_message = await event.reply('`Looking for the answer in STC (2-3 minutes)...`')
        document_query, query = query.split(' ', 1)

        answer = await self.application.cybrex_ai.chat_document(
            document_query=document_query,
            query=query,
            n_chunks=5,
        )
        response = f'**{query} in {document_query}**\n🤖: {answer}'
        await event.reply(response)
        await wait_message.delete()
