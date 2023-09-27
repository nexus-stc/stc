import asyncio
import logging
import os
import re
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from datetime import (
    datetime,
    timedelta,
)
from functools import partial
from pydoc import locate
from urllib.parse import (
    quote,
    unquote,
)

from aiokit import AioThing

from library.pdftools.cleaner import clean_metadata
from library.pdftools.exceptions import (
    PdfProcessingError,
    PyPdfError,
)
from library.telegram.base import BaseTelegramClient
from library.telegram.utils import safe_execution
from library.textutils import DOI_REGEX
from tgbot.search_request_builder import get_type_icon
from tgbot.views.telegram.base_holder import BaseTelegramDocumentHolder
from tgbot.views.telegram.common import vote_button

INTERNAL_ID_REGEX = re.compile(r'\[.*]\(https://standard-template-construct\.org/#/nexus_science/(id\.[^)]*)\)')


def extract_internal_id(text):
    if internal_id_regex := re.search(INTERNAL_ID_REGEX, text):
        return unquote(internal_id_regex.group(1))


async def add_publisher_links(request_text, doi, crossref_client=None):
    if doi.startswith('10.1080/'):
        request_text += f' - [T&F](https://www.tandfonline.com/doi/pdf/{doi}?download=true)'
    elif doi.startswith('10.1111/'):
        request_text += f' - [Wiley](https://onlinelibrary.wiley.com/doi/pdf/{doi})'
    elif doi.startswith('10.1007'):
        request_text += f' - [Springer](https://link.springer.com/content/pdf/{doi}.pdf)'
    elif doi.startswith('10.1016/') and crossref_client:
        try:
            metadata = await crossref_client.works(doi)
            if 'alternative-id' in metadata:
                selected = metadata['alternative-id'][0]
                request_text += f' - [Elsevier](https://www.sciencedirect.com/science/article/pii/{selected}/pdfft?isDTMRedir=true&download=true)'
        except Exception:
            pass
    return request_text


class LibrarianService(AioThing):
    def __init__(self, application, data_directory, auth_hook_dir, config):
        super().__init__()
        self.application = application

        if not os.path.exists(data_directory):
            os.mkdir(data_directory)

        self.admin_telegram_client = BaseTelegramClient(
            app_id=config['admin']['app_id'],
            app_hash=config['admin']['app_hash'],
            phone=config['admin']['phone'],
            database={'session_id': os.path.join(data_directory, "admin.sdb")},
            proxy_config=config['admin'].get('mtproxy') or None,
            auth_hook_dir=auth_hook_dir,
        )
        self.bot_telegram_client = BaseTelegramClient(
            app_id=config['bot']['app_id'],
            app_hash=config['bot']['app_hash'],
            bot_token=config['bot']['bot_token'],
            database={'session_id': os.path.join(data_directory, "librarian.sdb")},
            proxy_config=config['bot'].get('mtproxy') or None,
        )
        self.group_name = config['group_name']
        self.librarian_bot_name = config['bot']['bot_name']
        self.requests = {}
        self.cleanup_task = None
        self.pool = ProcessPoolExecutor(8)

    async def cleanup(self, collect_task):
        try:
            while 1:
                logging.getLogger('debug').debug({
                    'action': 'delete_outdated',
                    'mode': 'librarian_service',
                    'n': len(self.requests),
                })
                await self.delete_messages(before_date=time.mktime((datetime.utcnow() - timedelta(hours=46)).timetuple()))
                await collect_task
                logging.getLogger('debug').debug({
                    'action': 'check_already_uploaded',
                    'mode': 'librarian_service',
                    'n': len(self.requests),
                })
                for internal_id in list(self.requests.keys()):
                    field, value = internal_id.split(':', 1)
                    if document := await self.application.summa_client.get_one_by_field_value(
                        'nexus_science',
                        field,
                        value
                    ):
                        document_holder = BaseTelegramDocumentHolder(document)
                        if document_holder.get_links().get_link_with_extension('pdf'):
                            await self.delete_request(internal_id)
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logging.getLogger('debug').debug({
                'action': 'cleanup_cancelled',
                'mode': 'librarian_service',
            })
        except Exception as e:
            logging.getLogger('error').error({
                'action': 'cleanup_failed',
                'mode': 'librarian_service',
                'error': str(e),
                'tb': traceback.format_exc()
            })

    async def start(self):
        logging.getLogger('debug').debug({
            'action': 'start',
            'mode': 'librarian_service',
            'group_name': self.group_name,
        })
        submit_handler_cls = locate('tgbot.handlers.submit.SubmitHandler')
        vote_handler_cls = locate('tgbot.handlers.vote.VoteHandler')
        librarian_text_handler_cls = locate('tgbot.handlers.librarian.LibrarianTextHandler')

        submit_handler_cls(self.application, {}).register_for(self.bot_telegram_client, self.librarian_bot_name)
        vote_handler_cls(self.application, {}).register_for(self.bot_telegram_client, self.librarian_bot_name)
        librarian_text_handler_cls(self.application, {}).register_for(self.bot_telegram_client, self.librarian_bot_name)

        await self.bot_telegram_client.start()
        await self.admin_telegram_client.start()

        collect_task = asyncio.create_task(self.collect_all_requests())

        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self.cleanup(collect_task))

    async def stop(self):
        if self.cleanup_task:
            logging.getLogger('debug').debug({
                'action': 'stop',
                'mode': 'librarian_service',
                'group_name': self.group_name,
            })
            self.cleanup_task.cancel()
            await self.cleanup_task
            self.cleanup_task = None

    def is_request(self, message):
        return message.text and message.text.startswith('#request')

    def is_file(self, message):
        return bool(message.media)

    def is_related_message(self, message):
        if message.text:
            if internal_id := extract_internal_id(message.text):
                return internal_id
            elif doi_regex := re.search(DOI_REGEX, message.raw_text):
                return f'id.dois:{doi_regex.group(1) + "/" + doi_regex.group(2)}'

    def try_download_media(self, message):
        return message.download_media(file=bytes)

    async def collect_all_requests(self):
        logging.getLogger('debug').debug({
            'action': 'collecting_requests',
            'mode': 'librarian_service',
            'is_sciparser_enabled': bool(self.application.sciparser),
        })
        async for message in self.admin_telegram_client.iter_messages(self.group_name):
            internal_id = self.is_related_message(message)
            is_request = self.is_request(message)
            is_file = self.is_file(message)

            if not internal_id or (not is_request and not is_file):
                continue

            if is_request:
                logging.getLogger('debug').debug({
                    'action': 'add_existing',
                    'mode': 'librarian_service',
                    'internal_id': internal_id,
                })
                if internal_id in self.requests:
                    await self.admin_telegram_client.delete_messages(self.group_name, [self.requests[internal_id]])
                self.requests[internal_id] = message.id

            field, value = internal_id.split(':', 1)
            if self.application.sciparser and field in ('doi', 'id.dois') and is_file:
                if data := await self.try_download_media(message):
                    logging.getLogger('debug').debug({
                        'action': 'found_media',
                        'mode': 'librarian_service',
                        'filesize': len(data),
                    })
                    try:
                        processed_document = await self.application.sciparser.parse_paper({'data': data})
                        if not processed_document or 'doi' not in processed_document:
                            continue
                    except Exception as e:
                        logging.getLogger('warning').warning({
                            'action': 'failed_to_recognize',
                            'mode': 'librarian_service',
                            'internal_id': internal_id,
                            'filesize': len(data),
                            'error': str(e)
                        })
                        continue
                    doi = processed_document['doi'].lower().strip()
                    if value != doi:
                        logging.getLogger('debug').debug({
                            'action': 'doi_hint_mismatch',
                            'mode': 'librarian_service',
                            'doi': doi,
                            'doi_hint': value,
                        })
                        continue
                    document = await self.application.summa_client.get_one_by_field_value('nexus_science', 'id.dois', doi)
                    if not document:
                        continue
                    try:
                        data = await asyncio.wait_for(
                            asyncio.get_running_loop().run_in_executor(
                                self.pool,
                                partial(clean_metadata, data, doi=doi)
                            ),
                            timeout=600.0,
                        )
                    except asyncio.TimeoutError:
                        logging.getLogger('warning').warning({
                            'action': 'timeout',
                            'mode': 'librarian_service',
                            'doi': doi,
                        })
                    await self.application.file_flow.pin_add(document, data)
                    try:
                        await self.admin_telegram_client.delete_messages(self.group_name, [message.id])
                        await self.delete_request(internal_id)
                    except Exception as e:
                        logging.getLogger('error').error({
                            'action': 'fail_to_delete',
                            'doi': doi,
                            'mode': 'librarian_service',
                            'error': str(e)
                        })
        logging.getLogger('debug').debug({
            'action': 'collected',
            'mode': 'librarian_service',
            'requests': len(self.requests)
        })

    async def add_coordinates(self, document_holder, internal_id):
        field, value = internal_id.split(':', 1)

        if field == 'doi' or field == 'id.dois':
            prefix = value.split('/')[0].split('.', 1)[1].replace('.', '_')
            tail = f'#p_{prefix} [{value}](https://doi.org/{quote(value)})'
            tail = await add_publisher_links(tail, value, self.application.metadata_retriever.crossref_client)
            return tail
        elif field == 'id.internal_iso':
            link = (
                document_holder.view_builder('en')
                .add_external_provider_link(label=False, on_newline=True, text=document_holder.iso_id.upper())
                .build()
            )
            tail = f'#iso {link}'
            return tail
        elif field == 'id.pubmed_id':
            link = (
                document_holder.view_builder('en')
                .add_external_provider_link(label=False, on_newline=True, text=f'PMID:{document_holder.pubmed_id}')
                .build()
            )
            tail = f'#pubmed {link}'
            return tail
        else:
            raise ValueError("Unsupported internal id")

    async def request(self, document_holder):
        internal_id = document_holder.get_internal_id()
        type_ = document_holder.type

        if internal_id not in self.requests:
            logging.getLogger('statbox').info({
                'action': 'send_request',
                'mode': 'librarian_service',
                'internal_id': internal_id,
                'type': type_,
            })
            coordinates = await self.add_coordinates(document_holder, internal_id)
            request_text = f'#request [{get_type_icon(type_)}](https://standard-template-construct.org/#/nexus_science/{quote(internal_id)}) {coordinates}'
            message = await self.bot_telegram_client.send_message(
                self.group_name,
                request_text,
                link_preview=False,
            )
            self.requests[internal_id] = message.id
        return self.requests[internal_id]

    async def delete_request(self, internal_id: str):
        message_id = self.requests.pop(internal_id, None)
        logging.getLogger('statbox').info({
            'action': 'delete_request',
            'mode': 'librarian_service',
            'internal_id': internal_id,
            'message_id': message_id,
        })
        if message_id:
            async with safe_execution():
                await self.admin_telegram_client.delete_messages(self.group_name, message_id)

    async def delete_messages(self, before_date, document_only=False):
        messages = []
        async for message in self.admin_telegram_client.iter_messages(self.group_name):
            if (
                time.mktime(message.date.timetuple()) < before_date
                and (not document_only or message.document)
                and not message.pinned
            ):
                internal_id = self.is_related_message(message)
                if internal_id and self.is_request(message):
                    self.requests.pop(internal_id, None)
                messages.append(message)
        async with safe_execution():
            await self.admin_telegram_client.delete_messages(self.group_name, messages)

    async def process_file(self, event, request_context, document):
        reply_to = None
        reply_message = await event.get_reply_message()
        if reply_message:
            reply_to = reply_message.id

        file = await event.message.download_media(file=bytes)
        await event.delete()

        holder = BaseTelegramDocumentHolder(document)
        short_abstract = (
            holder.view_builder(request_context.chat['language'])
            .add_short_description(with_hidden_id=True)
            .add_external_provider_link(label=True, on_newline=True)
            .build()
        )
        caption = f"{short_abstract}\n\n#voting"
        try:
            if holder.doi:
                file = await asyncio.wait_for(
                    asyncio.get_running_loop().run_in_executor(
                        self.pool,
                        partial(clean_metadata, file, doi=holder.doi)
                    ),
                    timeout=600.0,
                )
            if holder.iso_id and 'ieee' in holder.iso_id:
                file = await asyncio.wait_for(
                    asyncio.get_running_loop().run_in_executor(
                        self.pool,
                        partial(clean_metadata, file, doi='10.1109/std')
                    ),
                    timeout=600.0,
                )
        except PyPdfError:
            caption += '\n\n**File is possibly corrupted, check manually**'
        except (PdfProcessingError, RecursionError) as e:
            logging.error({
                'action': 'cleanup failed',
                'error': str(e),
            })
            caption += '\n\n**File cannot be cleaned out of metadata, check manually**'
        except asyncio.TimeoutError:
            caption += '\n\n**Cleaning timeouted, check manually**'
        caption += '\n\nCorrect: \nIncorrect: '

        return await self.application.librarian_service.bot_telegram_client.send_file(
            attributes=event.document.attributes,
            caption=caption,
            entity=request_context.chat['chat_id'],
            reply_to=reply_to,
            buttons=[
                vote_button(request_context.chat['language'], 'correct'),
                vote_button(request_context.chat['language'], 'incorrect'),
            ],
            file=file,
        )
