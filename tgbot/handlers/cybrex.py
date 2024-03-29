import asyncio
import re
import shlex

from telethon import events

from library.telegram.base import RequestContext

from .base import BaseHandler


class CybrexHandler(BaseHandler):
    filter = events.NewMessage(incoming=True, pattern=re.compile(r'^/cybrex(?:@\w+)?(?:\s+)?(.*)?$', re.DOTALL))
    is_group_handler = True

    def parse_command(self, query):
        args = []
        kwargs = {}
        argv = shlex.split(query)
        cmd, argv = argv[0], argv[1:]
        for arg in argv:
            if arg.startswith('-'):
                arg = arg.lstrip('-')
                k, v = arg.split('=', 1)
                k = k.replace('-', '_')
                try:
                    v = int(v)
                except ValueError:
                    try:
                        v = float(v)
                    except ValueError:
                        pass
                kwargs[k.replace('-', '_')] = v
            else:
                args.append(arg)
        return cmd, args, kwargs

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        session_id = self.generate_session_id()
        request_context.add_default_fields(mode='cybrex', session_id=session_id)
        request_context.statbox(action='show', sender_id=event.sender_id, event=str(event))

        is_allowed = event.sender_id and int(event.sender_id) in self.application.config['application']['cybrex_whitelist']
        is_allowed = is_allowed or (
            event.sender_id is None
            and request_context.chat['chat_id'] in self.application.config['application']['cybrex_whitelist']
        )
        if not is_allowed:
            return await event.reply('Only People of Nexus can call me')

        if not self.application.cybrex_ai:
            return await event.reply('Cybrex is disabled for now')

        query = event.pattern_match.group(1).strip()
        if not query:
            text = "My name is Cybrex and I can respond queries based on STC data."
            return await event.reply(text)

        reply_message = await event.get_reply_message()
        request_context.statbox(action='found_reply_message', reply_message=str(reply_message))

        if reply_message and reply_message.raw_text:
            wait_message = await event.reply('`All right, wait a sec...`')

            text = reply_message.raw_text
            cybrex_response = await self.application.cybrex_ai.general_text_processing(query, text)
            response = f'🤔 **{query}**'
            response = f'{response}\n\n🤖: {cybrex_response.answer.strip()}'
            return await asyncio.gather(
                wait_message.delete(),
                reply_message.reply(response),
            )

        wait_message = await event.reply('`Looking for the answer in STC...`')

        cli = {
            'chat-doc': self.application.cybrex_ai.chat_document,
            'chat-sci': self.application.cybrex_ai.chat_science,
            'semantic-search': self.application.cybrex_ai.semantic_search,
            'sum-doc': self.application.cybrex_ai.summarize_document,
        }

        cmd, args, kwargs = self.parse_command(query)
        response = await cli[cmd](*args, **kwargs)
        show_texts = False

        if cmd == 'semantic-search':
            answer, chunks = None, [scored_chunk.chunk for scored_chunk in response]
            show_texts = True
        else:
            answer, chunks = response.answer, response.chunks

        response = f'🤔 **{args[0]}**'
        if answer:
            response = f'{response}\n\n🤖: {answer}'

        references = []
        visited = set()
        for chunk in chunks[:3]:
            field, value = chunk.document_id.split(':', 2)
            document_id = f'{field}:{value}'
            title = chunk.title.split("\n")[0]
            reference = f' - **{title}** - `{document_id}`'
            if show_texts:
                reference += f'\n**Text:** {chunk.text}'
            else:
                if document_id in visited:
                    continue
            visited.add(document_id)
            references.append(reference)

        if show_texts:
            references = '\n\n'.join(references)
        else:
            references = '\n'.join(references)
        if references:
            response += f'\n\n**References:**\n\n{references}'

        return await asyncio.gather(
            wait_message.delete(),
            event.reply(response),
        )
