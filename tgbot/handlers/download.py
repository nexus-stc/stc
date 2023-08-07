import asyncio
import time

import aiohttp
from aiobaseclient.exceptions import (
    ServiceUnavailableError,
    TemporaryError,
)
from izihawa_utils.common import filter_none
from telethon import (
    Button,
    events,
)
from telethon.errors import rpcerrorlist
from telethon.tl.types import DocumentAttributeFilename
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from library.telegram.base import RequestContext
from library.telegram.utils import safe_execution
from tgbot.app.exceptions import DownloadError
from tgbot.translations import t
from tgbot.views.telegram.base_holder import BaseHolder
from tgbot.views.telegram.common import (
    recode_base64_to_base36,
    remove_button,
)
from tgbot.views.telegram.progress_bar import (
    ProgressBar,
    ProgressBarLostMessageError,
)

from .base import (
    BaseCallbackQueryHandler,
    LongTask,
)


async def download_thumb(isbns, timeout=5.0):
    if not isbns:
        return
    try:
        return await asyncio.wait_for(do_download_thumb(isbns[0], timeout), timeout)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        return


async def do_download_thumb(isbn, timeout=5.0):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.get(f'https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg') as resp:
            data = await resp.read()
            if resp.status == 200 and data[:6] != b'GIF89a':
                return data


async def first_task(*tasks):
    done, pending = await asyncio.wait(tasks, timeout=1200, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    for task in done:
        return task.result()


class DownloadTask(LongTask):
    def __init__(
        self,
        application,
        request_context,
        document_holder,
        download_link,
    ):
        super().__init__(application, request_context, document_holder)
        self.download_link = download_link

    async def long_task(self, request_context: RequestContext):
        throttle_secs = 3.0

        async def _on_fail():
            await self.application.get_telegram_client(request_context.bot_name).send_message(
                request_context.chat['chat_id'],
                t('MAINTENANCE', request_context.chat['language']).format(
                    error_picture_url=self.application.config['application']['error_picture_url']
                ),
                buttons=request_context.personal_buttons()
            )

        telegram_file_id = await self.application.database.get_cached_file(request_context.bot_name, self.download_link['cid'])
        if not telegram_file_id:
            telegram_file_id = self.application.get_telegram_client(request_context.bot_name).get_cached_file_id(self.download_link['cid'])
        if telegram_file_id:
            async with safe_execution(error_log=request_context.error_log):
                await self.send_file(
                    document_holder=self.document_holder,
                    download_link=self.download_link,
                    file=telegram_file_id,
                    request_context=request_context,
                )
                request_context.statbox(action='cache_hit')
                return

        async with safe_execution(
            error_log=request_context.error_log,
            on_fail=_on_fail,
        ):
            start_time = time.time()
            filename = self.document_holder.get_purified_name(self.download_link) + '.' + self.download_link['extension']
            progress_bar_download = ProgressBar(
                telegram_client=self.application.get_telegram_client(request_context.bot_name),
                request_context=request_context,
                banner=t("LOOKING_AT", request_context.chat['language']),
                header=f'⬇️ {filename}',
                tail_text=t('TRANSMITTED_FROM', request_context.chat['language']),
                source='IPFS',
                throttle_secs=throttle_secs,
                last_call=start_time,
            )
            try:
                thumb_task = asyncio.create_task(download_thumb(self.document_holder.isbns))
                file = await self.download_document(
                    cid=self.download_link['cid'],
                    progress_bar=progress_bar_download,
                    request_context=request_context,
                    filesize=self.download_link.get('filesize'),
                )
                if file:
                    request_context.statbox(
                        action='downloaded',
                        duration=time.time() - start_time,
                        len=len(file),
                    )
                    progress_bar_upload = ProgressBar(
                        telegram_client=self.application.get_telegram_client(request_context.bot_name),
                        request_context=request_context,
                        message=progress_bar_download.message,
                        banner=t("LOOKING_AT", request_context.chat["language"]),
                        header=f'⬇️ {filename}',
                        tail_text=t('UPLOADED_TO_TELEGRAM', request_context.chat["language"]),
                        throttle_secs=throttle_secs,
                        last_call=progress_bar_download.last_call,
                    )
                    uploaded_message = await self.send_file(
                        document_holder=self.document_holder,
                        download_link=self.download_link,
                        file=file,
                        progress_callback=progress_bar_upload.callback,
                        request_context=self.request_context,
                        thumb=await thumb_task
                    )
                    asyncio.create_task(self.application.database.put_cached_file(
                        request_context.bot_name,
                        self.download_link['cid'],
                        uploaded_message.file.id,
                    ))
                    request_context.statbox(
                        action='uploaded',
                        duration=time.time() - start_time,
                        file_id=uploaded_message.file.id
                    )
                else:
                    request_context.statbox(
                        action='not_found',
                        duration=time.time() - start_time,
                    )
                    await self.respond_not_found(
                        request_context=request_context,
                        document_holder=self.document_holder,
                    )
            except (ServiceUnavailableError, DownloadError) as e:
                request_context.error_log(e)
                raise
            except ProgressBarLostMessageError:
                self.request_context.statbox(
                    action='user_canceled',
                    duration=time.time() - start_time,
                )
            except asyncio.CancelledError:
                await self.external_cancel()
            finally:
                messages = filter_none([progress_bar_download.message])
                if messages:
                    async with safe_execution(error_log=request_context.error_log):
                        await self.application.get_telegram_client(request_context.bot_name).delete_messages(
                            request_context.chat['chat_id'],
                            messages
                        )
                request_context.debug_log(action='deleted_progress_message')

    async def respond_not_found(self, request_context: RequestContext, document_holder):
        return await self.application.get_telegram_client(request_context.bot_name).send_message(
            request_context.chat['chat_id'],
            t("SOURCES_UNAVAILABLE", request_context.chat["language"]).format(
                document=document_holder.doi or document_holder.view_builder(
                    request_context.chat["language"]).add_title(bold=False).build()
            ),
            buttons=request_context.personal_buttons()
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(5.0),
        retry=retry_if_exception_type(TemporaryError),
        reraise=True,
    )
    async def download_document(self, cid, request_context, progress_bar=None, filesize=None):
        request_context.statbox(
            action='do_request',
            cid=cid,
        )
        if progress_bar:
            await progress_bar.show_banner()
        collected = bytearray()
        async for chunk in self.application.ipfs_http_client.get_iter(cid):
            collected.extend(chunk)
            if progress_bar:
                await progress_bar.callback(len(collected), filesize)
        return bytes(collected)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((rpcerrorlist.TimeoutError, ValueError)),
    )
    async def send_file(
        self,
        document_holder,
        download_link,
        file,
        request_context,
        progress_callback=None,
        chat_id=None,
        reply_to=None,
        thumb=None,
    ):
        buttons = []
        if request_context.is_personal_mode() and document_holder.index_alias == 'nexus_science':
            buttons.append(Button.switch_inline(
                text='👎 Broken or incorrect file',
                query=f'/r_{download_link["cid"]}',
                same_peer=True
            ))
        if not buttons:
            buttons = None
        short_abstract = (
            document_holder.view_builder(request_context.chat["language"])
            .add_short_description()
            .add_external_provider_link(label=True, on_newline=True, text=document_holder.doi)
            .build()
        )
        caption = (
            f"{short_abstract}\n"
            f"@{self.application.config['telegram']['related_channel']}"
        )
        if self.application.get_telegram_client(request_context.bot_name):
            filename = document_holder.get_purified_name(download_link) + '.' + download_link['extension']

            message = await self.application.get_telegram_client(request_context.bot_name).send_file(
                attributes=[DocumentAttributeFilename(filename)],
                buttons=buttons,
                caption=caption,
                entity=chat_id or request_context.chat['chat_id'],
                file=file,
                progress_callback=progress_callback,
                reply_to=reply_to,
                thumb=thumb,
            )
            request_context.statbox(action='sent')
            return message


class DownloadHandler(BaseCallbackQueryHandler):
    filter = events.CallbackQuery(pattern='^/d_([A-Za-z0-9_-]+)$')
    is_group_handler = True

    def parse_pattern(self, event: events.ChatAction):
        cid = recode_base64_to_base36(event.pattern_match.group(1).decode())
        return cid

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        cid = self.parse_pattern(event)
        request_context.add_default_fields(mode='download', cid=cid)
        request_context.statbox(action='get')
        scored_document = await self.get_scored_document(self.bot_index_aliases, 'cid', cid)
        if not scored_document:
            return await event.answer(
                f'{t("CID_DISAPPEARED", request_context.chat["language"])}',
            )
        document_holder = BaseHolder.create(scored_document)
        download_link = None
        for link in document_holder.links:
            if link['cid'] == cid:
                download_link = link

        if self.application.user_manager.has_task(request_context.chat['chat_id'], DownloadTask.task_id_for(document_holder)):
            async with safe_execution(is_logging_enabled=False):
                await event.answer(
                    f'{t("ALREADY_DOWNLOADING", request_context.chat["language"])}',
                )
                await remove_button(event, '⬇️', and_empty_too=True, link_preview=document_holder.has_cover())
                return
        if self.application.user_manager.hit_limits(request_context.chat['chat_id']):
            async with safe_execution(is_logging_enabled=False):
                return await event.answer(
                    f'{t("TOO_MANY_DOWNLOADS", request_context.chat["language"])}',
                )
        await remove_button(event, '⬇️', and_empty_too=True, link_preview=document_holder.has_cover())
        return DownloadTask(
            application=self.application,
            document_holder=document_holder,
            request_context=request_context,
            download_link=download_link,
        ).schedule()
