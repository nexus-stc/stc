import asyncio
import logging
import os
import re
import time
import traceback
from datetime import datetime, timedelta

from aiokit import AioThing
from izihawa_utils.importlib import import_object

from library.pdftools.cleaner import clean_metadata
from library.pdftools.exceptions import PdfProcessingError, PyPdfError
from library.regexes import DOI_REGEX
from library.telegram.base import BaseTelegramClient
from library.telegram.utils import safe_execution
from tgbot.app.query_builder import get_type_icon
from tgbot.views.telegram.base_holder import BaseHolder
from tgbot.views.telegram.common import vote_button


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
                for doi in list(self.requests.keys()):
                    if document := await self.application.summa_client.get_one_by_field_value(
                        'nexus_science',
                        'doi',
                        doi.lower()
                    ):
                        if 'links' in document and document['links']['type'] == 'primary':
                            await self.delete_request(doi)
                await asyncio.sleep(3600)
        except Exception as e:
            logging.getLogger('error').error({
                'action': 'cleanup_failed',
                'mode': 'librarian_service',
                'error': str(e),
                'tb': traceback.format_tb()
            })
        except asyncio.CancelledError:
            logging.getLogger('debug').debug({
                'action': 'cleanup_cancelled',
                'mode': 'librarian_service',
            })

    async def start(self):
        logging.getLogger('debug').debug({
            'action': 'start',
            'mode': 'librarian_service',
            'group_name': self.group_name,
        })
        submit_handler_cls = import_object('tgbot.handlers.submit.SubmitHandler')
        vote_handler_cls = import_object('tgbot.handlers.vote.VoteHandler')
        librarian_text_handler_cls = import_object('tgbot.handlers.librarian.LibrarianTextHandler')

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
        if message.raw_text and message.raw_text.startswith('#request'):
            doi_regex = re.search(DOI_REGEX, message.raw_text)
            if doi_regex:
                return doi_regex.group(1) + '/' + doi_regex.group(2)

    def is_file(self, message):
        if message.raw_text:
            doi_regex = re.search(DOI_REGEX, message.raw_text)
            if doi_regex:
                return doi_regex.group(1) + '/' + doi_regex.group(2)

    def try_download_media(self, message):
        return message.download_media(file=bytes)

    async def collect_all_requests(self):
        logging.getLogger('debug').debug({
            'action': 'collecting_requests',
            'mode': 'librarian_service',
            'is_grobid_enabled': bool(self.application.grobid_client),
        })
        async for message in self.admin_telegram_client.iter_messages(self.group_name):
            if doi := self.is_request(message):
                self.requests[doi] = message.id
            if self.application.grobid_client:
                if data := await self.try_download_media(message):
                    logging.getLogger('debug').debug({
                        'action': 'found_media',
                        'mode': 'librarian_service',
                        'filesize': len(data),
                    })
                    processed_document = await self.application.grobid_client.process_fulltext_document(pdf_file=data)
                    if not processed_document or 'doi' not in processed_document:
                        continue
                    doi = processed_document['doi'].lower().strip()
                    if doi_hint := self.is_file(message):
                        if doi_hint != doi:
                            logging.getLogger('debug').debug({
                                'action': 'doi_hint_mismatch',
                                'mode': 'librarian_service',
                                'doi': doi,
                                'doi_hint': doi_hint,
                            })
                            continue
                    document = await self.application.summa_client.get_one_by_field_value('nexus_science', 'doi', doi)
                    try:
                        data = await asyncio.wait_for(
                            asyncio.get_running_loop().run_in_executor(
                                None,
                                lambda: clean_metadata(data, doi=doi)
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
                        await self.delete_request(doi)
                    except Exception as e:
                        logging.getLogger('error').error({
                            'action': 'fail_to_delete',
                            'doi': doi,
                            'mode': 'librarian_service',
                            'error': str(e)
                        })
        logging.getLogger('debug').debug({
            'action': 'collect',
            'mode': 'librarian_service',
            'requests': len(self.requests)
        })

    async def request(self, doi: str, type_):
        if doi not in self.requests:
            logging.getLogger('statbox').info({
                'action': 'send_request',
                'mode': 'librarian_service',
                'doi': doi,
                'type': type_,
            })
            prefix = doi.split('/')[0].split('.', 1)[1].replace('.', '_')
            request_text = f'#request #p_{prefix} {get_type_icon(type_)} https://doi.org/{doi}'
            request_text = await add_publisher_links(request_text, doi, self.application.metadata_retriever.crossref_client)
            message = await self.bot_telegram_client.send_message(
                self.group_name,
                request_text,
                link_preview=False,
            )
            self.requests[doi] = message.id
        return self.requests[doi]

    async def delete_request(self, doi: str):
        message_id = self.requests.pop(doi, None)
        logging.getLogger('statbox').info({
            'action': 'delete_request',
            'mode': 'librarian_service',
            'doi': doi,
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
                if doi := self.is_request(message):
                    self.requests.pop(doi, None)
                messages.append(message)
        async with safe_execution():
            await self.admin_telegram_client.delete_messages(self.group_name, messages)

    async def process_file(self, event, request_context, document):
        reply_to = None
        reply_message = await event.get_reply_message()
        if reply_message:
            reply_to = reply_message.id

        pdf_file = await event.message.download_media(file=bytes)
        await event.delete()

        holder = BaseHolder.create(document)
        short_abstract = (
            holder.view_builder(request_context.chat['language'])
            .add_short_abstract()
            .add_external_provider_link(label=True, on_newline=True, text=holder.doi)
            .build()
        )
        caption = f"{short_abstract}\n\n#voting"
        try:
            pdf_file = await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: clean_metadata(pdf_file, doi=holder.doi)
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
            file=pdf_file,
        )
