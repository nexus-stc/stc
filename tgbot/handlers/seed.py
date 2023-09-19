import asyncio
import os
import re
import tempfile
from urllib.parse import quote

import ipfs_hamt_directory_py
from stc_geck.advices import LinksWrapper
from telethon import events
from telethon.tl.types import DocumentAttributeFilename

from library.telegram.base import RequestContext
from library.telegram.common import close_button
from library.telegram.utils import safe_execution
from library.textutils.utils import cast_string_to_single_string
from tgbot.translations import t
from tgbot.views.telegram.base_holder import BaseTelegramDocumentHolder

from .base import BaseHandler


def create_car(documents, name_template) -> (str, bytes):
    with tempfile.TemporaryDirectory() as td:
        input_data = os.path.join(td, 'input_data.txt')
        output_car = os.path.join(td, 'output.car')
        with open(input_data, 'wb') as f:
            for document in documents:
                document_holder = BaseTelegramDocumentHolder.create(document)
                links = LinksWrapper(document_holder.links)
                if link := links.get_link_with_extension('pdf'):
                    item_name = name_template.format(
                        doi=document_holder.doi,
                        md5=document_holder.md5,
                        suggested_filename=document_holder.get_purified_name({
                            'doi': document_holder.doi,
                            'cid': link['cid'],
                        }),
                    ) + '.' + 'pdf'
                    f.write(quote(item_name, safe='').encode())
                    f.write(b' ')
                    f.write(link['cid'].encode())
                    f.write(b' ')
                    f.write(str(link.get('filesize') or 0).encode())
                    f.write(b'\n')
                if link := links.get_link_with_extension('epub'):
                    item_name = name_template.format(
                        doi=document_holder.doi,
                        md5=document_holder.md5,
                        suggested_filename=document_holder.get_purified_name({
                            'doi': document_holder.doi,
                            'cid': link['cid'],
                        }),
                    ) + '.' + 'epub'
                    f.write(quote(item_name, safe='').encode())
                    f.write(b' ')
                    f.write(link['cid'].encode())
                    f.write(b' ')
                    f.write(str(link.get('filesize') or 0).encode())
                    f.write(b'\n')
        cid = ipfs_hamt_directory_py.from_file(input_data, output_car, td)
        with open(output_car, 'rb') as f:
            return cid, f.read()


class SeedHandler(BaseHandler):
    filter = events.NewMessage(
        incoming=True,
        pattern=re.compile(
            r'^/(r)?seed(?:@\w+)?(?:(?:\s+(\d+))?(?:\s+(\d+))?(?:[^\S\r\n]+([\w{}\-_]+))?\n*(.*))?$',
            flags=re.MULTILINE,
        ),
    )
    is_group_handler = False

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        session_id = self.generate_session_id()
        request_context.add_default_fields(mode='seed', session_id=session_id)
        max_page_size = 100_000

        random_seed = True if event.pattern_match.group(1) else False

        if string_page := event.pattern_match.group(2):
            page = int(string_page.strip() or 0)
        else:
            page = 0

        if string_page_size := event.pattern_match.group(3):
            page_size = int(string_page_size.strip())
        else:
            page_size = page
            page = 0

        name_template = event.pattern_match.group(4)
        if not name_template or not name_template.strip():
            name_template = '{suggested_filename}'

        if page_size > max_page_size and event.chat_id not in self.application.config['application']['bypass_maintenance']:
            return await self.application.get_telegram_client(request_context.bot_name).send_message(
                request_context.chat['chat_id'],
                t("REQUESTED_TOO_MUCH", request_context.chat['language']).format(page_size=max_page_size),
            )
        string_query = event.pattern_match.group(5)

        if not string_query and not string_page_size and not string_page:
            request_context.statbox(action='help')
            return await event.reply(t('SEED_HELP', language=request_context.chat['language']), buttons=[close_button()])

        wait_message = await event.respond(t('SEED_GENERATION', language=request_context.chat['language']))
        request_context.statbox(
            action='request',
            offset=page * page_size,
            limit=page_size,
            query=string_query,
        )

        if random_seed:
            query, query_traits = self.application.search_request_builder.process(
                string_query.strip(),
                is_fieldnorms_scoring_enabled=False,
                extra_filter={'term': {'field': 'links.extension', 'value': 'pdf'}},
                fields={
                    'nexus_science': ['links', 'id', 'title', 'authors', 'issued_at', 'metadata'],
                },
                collector='reservoir_sampling',
                limit=page_size,
                default_query_language=request_context.chat['language'],
            )

            response = await self.application.summa_client.search(query)
            documents = response.collector_outputs[0].documents.scored_documents
            count = response.collector_outputs[1].count.count
        else:
            query, query_traits = self.application.search_request_builder.process(
                string_query.strip(),
                is_fieldnorms_scoring_enabled=False,
                extra_filter={'term': {'field': 'links.extension', 'value': 'pdf'}},
                fields=['links', 'id', 'title', 'authors', 'issued_at', 'metadata'],
                offset=page * page_size,
                limit=page_size,
                default_query_language=request_context.chat['language'],
            )

            response = await self.application.summa_client.search(query)
            documents = response.collector_outputs[0].documents.scored_documents
            count = response.collector_outputs[1].count.count

        # Nothing found
        if not len(documents):
            async with safe_execution(error_log=request_context.error_log):
                await self.application.get_telegram_client(request_context.bot_name).delete_messages(
                    request_context.chat['chat_id'], [wait_message.id])
                return await self.application.get_telegram_client(request_context.bot_name).send_message(
                    request_context.chat['chat_id'],
                    t("COULD_NOT_FIND_ANYTHING", request_context.chat['language']),
                )

        casted_query = cast_string_to_single_string(string_query) if string_query else None
        if not casted_query:
            casted_query = 'cids'
        filename = f'{casted_query[:16]}-{page}-{string_page_size}-{count}.car'
        page_head = f'**Page:** {page}\n' if not random_seed else ''

        root_cid, file = await asyncio.get_event_loop().run_in_executor(None, lambda: create_car(documents, name_template))

        await self.application.get_telegram_client(request_context.bot_name).send_file(
            attributes=[DocumentAttributeFilename(filename)],
            buttons=[close_button()],
            caption=f'{page_head}'
                    f'**Page size:** {string_page_size}\n'
                    f'**Total:** {count}\n\n'
                    f'**Root CID:** `{root_cid}`\n\n'
                    f'**Import (without pinning):** \n'
                    f'`ipfs dag import --stats --pin-roots=false {filename}`\n\n'
                    f'**Import:** \n'
                    f'`ipfs dag import --stats {filename}`\n\n'
                    f'**View:** \n'
                    f'In Terminal: `ipfs ls --resolve-type=false --size=false -s {root_cid}`\n'
                    f'In Browser: https://ipfs.io/ipfs/{root_cid}',
            entity=request_context.chat['chat_id'],
            file=file,
            reply_to=event,
        )
        async with safe_execution(error_log=request_context.error_log):
            await self.application.get_telegram_client(request_context.bot_name).delete_messages(request_context.chat['chat_id'], [wait_message.id])
