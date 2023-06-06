import asyncio
from abc import ABC
from functools import partial

from izihawa_utils.random import random_string
from telethon import TelegramClient, events, functions
from telethon.errors import QueryIdInvalidError

from library.telegram.base import RequestContext
from library.telegram.common import close_button
from library.telegram.utils import safe_execution
from tgbot.app.application import TelegramApplication
from tgbot.translations import t


def get_username(event: events.ChatAction, chat):
    if event.is_group or event.is_channel:
        return str(event.chat_id)
    else:
        return chat.username


def get_language(event: events.ChatAction, chat):
    if event.is_group or event.is_channel:
        return 'en'
    return chat.lang_code


class LongTask:
    def __init__(
        self,
        application,
        request_context,
        document_holder,
    ):
        self.application = application
        self.request_context = request_context
        self.document_holder = document_holder
        self.task = None

    @classmethod
    def task_id_for(cls, holder):
        return f'{cls.__name__}_{holder.get_internal_id()}'

    @property
    def task_id(self):
        return self.task_id_for(self.document_holder)

    def schedule(self):
        self.application.long_tasks.add(self)
        self.application.user_manager.add_task(self.request_context.chat['chat_id'], self.task_id)
        self.task = asyncio.create_task(
            self.long_task(
                request_context=self.request_context,
            )
        )
        self.task.add_done_callback(self.done_callback)
        return self.task

    def done_callback(self, f):
        self.application.long_tasks.remove(self)
        self.application.user_manager.remove_task(
            self.request_context.chat['chat_id'],
            self.task_id,
        )

    async def long_task(self, request_context: RequestContext):
        raise NotImplementedError()

    async def external_cancel(self):
        self.request_context.statbox(action='externally_canceled', task_id=self.task_id)
        self.task.cancel()
        await self.application.get_telegram_client(self.request_context.bot_name).send_message(
            self.request_context.chat['chat_id'],
            t("DOWNLOAD_CANCELED", self.request_context.chat["language"]).format(
                document=self.document_holder.view_builder(self.request_context.chat["language"]).add_title(
                    bold=False).build()
            ),
            buttons=self.request_context.personal_buttons()
        )


class BaseHandler(ABC):
    # Is handler working in the groups
    is_group_handler = False
    # Telethon filter
    filter = events.NewMessage(incoming=True)
    # Raises StopPropagation in the end of handling. It means this handler would be the last one in chain
    stop_propagation = True
    # If set to True then read_only mode will disable handler
    writing_handler = False

    def __init__(self, application: TelegramApplication, bot_config, extra_warning=None):
        self.application = application
        self.bot_config = bot_config
        self.extra_warning = extra_warning

    async def get_scored_document(self, index_aliases, field: str, value: str):
        queries = self.application.query_processor.process(
            f'{field}:{value}',
            page_size=1,
            is_fieldnorms_scoring_enabled=False,
            index_aliases=index_aliases,
        )
        response = await self.application.summa_client.search(queries)
        if response.collector_outputs[0].documents.scored_documents:
            return response.collector_outputs[0].documents.scored_documents[0]

    def generate_session_id(self) -> str:
        return random_string(self.application.config['application']['session_id_length'])

    async def get_last_messages_in_chat(self, event: events.ChatAction, request_context: RequestContext):
        telegram_client = self.application.get_telegram_client(request_context.bot_name)
        messages_holder = await telegram_client(functions.messages.GetMessagesRequest(
            id=list(range(event.id + 1, event.id + 10)))
        )
        if messages_holder:
            return messages_holder.messages
        return []

    def register_for(self, telegram_client: TelegramClient, bot_name: str):
        telegram_client.add_event_handler(partial(self._wrapped_handler, bot_name=bot_name), self.filter)
        return self._wrapped_handler

    async def _send_fail_response(self, event: events.ChatAction, request_context: RequestContext):
        try:
            await event.reply(
                t('MAINTENANCE', request_context.chat['language']).format(
                    error_picture_url=self.application.config['application']['error_picture_url'],
                ),
                buttons=None if request_context.is_group_mode() else [close_button()]
            )
        except (ConnectionError, QueryIdInvalidError, ValueError) as e:
            request_context.error_log(e)

    async def _check_maintenance(self, event: events.ChatAction):
        if (
            self.application.config['application']['is_maintenance_mode']
            and event.chat_id not in self.application.config['application']['bypass_maintenance']
        ):
            await event.reply(
                t('UPGRADE_MAINTENANCE', 'en').format(
                    upgrade_maintenance_picture_url=self.application.config['application']
                    ['upgrade_maintenance_picture_url']
                ),
                buttons=None if (event.is_group or event.is_channel) else [close_button()]
            )
            raise events.StopPropagation()

    async def _check_read_only(self, event: events.ChatAction):
        if self.application.config['application'].get('is_read_only', False) and self.writing_handler:
            await event.reply(
                t('UPGRADE_MAINTENANCE', 'en').format(
                    upgrade_maintenance_picture_url=self.application.config['application']
                    ['upgrade_maintenance_picture_url']
                ),
                buttons=None if (event.is_group or event.is_channel) else [close_button()]
            )
            raise events.StopPropagation()

    async def _process_chat(self, event: events.ChatAction, request_id: str):
        event_chat = await event.get_chat()
        username = get_username(event, event_chat)
        language = get_language(event, event_chat)
        return dict(
            chat_id=event.chat_id,
            username=username,
            language=language,
        )

    async def _wrapped_handler(self, event: events.ChatAction, bot_name: str) -> None:
        # Checking group permissions
        if (event.is_group or event.is_channel) and not self.is_group_handler:
            return

        await self._check_maintenance(event=event)
        await self._check_read_only(event)

        request_id = RequestContext.generate_request_id(self.application.config['application']['request_id_length'])
        chat = await self._process_chat(event=event, request_id=request_id)

        request_context = RequestContext(
            bot_name=bot_name,
            chat=chat,
            request_id=request_id,
            request_id_length=self.application.config['application']['request_id_length'],
        )

        async with safe_execution(
            error_log=request_context.error_log,
            on_fail=lambda: self._send_fail_response(event, request_context),
        ):
            await self.handler(
                event,
                request_context=request_context,
            )
        if self.stop_propagation:
            raise events.StopPropagation()

    async def handler(self, event: events.ChatAction, request_context: RequestContext):
        raise NotImplementedError()


class BaseCallbackQueryHandler(BaseHandler, ABC):
    async def _send_fail_response(self, event, request_context: RequestContext):
        try:
            await event.answer(t('MAINTENANCE_WO_PIC', request_context.chat['language']))
        except (ConnectionError, QueryIdInvalidError) as e:
            request_context.error_log(e)
