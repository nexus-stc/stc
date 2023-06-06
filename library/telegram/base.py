import asyncio
import datetime
import logging
import os.path
from typing import Optional, Union

from aiokit import AioThing
from izihawa_loglib import error_log
from izihawa_utils.random import generate_request_id
from izihawa_utils.text import mask
from lru import LRU
from telethon import TelegramClient, connection, hints, sessions
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed  # noqa

from .common import close_button
from .session_backend import AlchemySessionContainer


class BaseTelegramClient(AioThing):
    def __init__(
        self,
        app_id: Union[int, str],
        app_hash: str,
        database: dict,
        phone: Optional[str] = None,
        password: Optional[str] = None,
        bot_token: Optional[str] = None,
        proxy_config: Optional[str] = None,
        flood_sleep_threshold: int = 60,
        catch_up: bool = False,
        auth_hook_dir: str = '/tmp'
    ):
        super().__init__()
        if not app_id or not app_hash:
            raise ValueError(
                'Your API ID or Hash cannot be empty or None. Set up telegram.app_id and/or telegram.app_hash'
            )
        self.app_id = app_id

        if proxy_config:
            proxy_config = {
                'connection': connection.tcpmtproxy.ConnectionTcpMTProxyRandomizedIntermediate,
                'proxy': proxy_config.split(':')
            }
        else:
            proxy_config = {}

        self._telegram_client = TelegramClient(
            self._get_session(database),
            app_id,
            app_hash,
            catch_up=catch_up,
            flood_sleep_threshold=flood_sleep_threshold,
            **proxy_config,
        )
        self.file_handle_cache = LRU(16)
        self.phone = phone
        self.password = password
        self.bot_token = bot_token
        self.auth_hook_dir = auth_hook_dir

    def __str__(self):
        return f'BaseTelegramClient(app_id={self.app_id}, phone={mask(self.phone)}, bot_token={mask(self.bot_token)})'

    def _get_session(self, database):
        if database.get('drivername') == 'postgresql':
            self.container = AlchemySessionContainer(
                f"{database['drivername']}://"
                f"{database['username']}:"
                f"{database['password']}@"
                f"{database['host']}:"
                f"{database['port']}/"
                f"{database['database']}",
                session=False,
                manage_tables=False,
            )
            return self.container.new_session(database['session_id'])
        else:
            return sessions.SQLiteSession(session_id=database['session_id'])

    @retry(retry=retry_if_exception_type(ConnectionError), stop=stop_after_attempt(3), wait=wait_fixed(5))
    async def start(self):
        logging.getLogger('statbox').debug({'mode': 'telegram', 'action': 'start', 'phone': self.phone, 'bot_token': self.bot_token})
        await self._telegram_client.start(
            phone=lambda: self.phone,
            bot_token=self.bot_token,
            password=self.polling_file(os.path.join(self.auth_hook_dir, 'telegram_password')),
            code_callback=self.polling_file(os.path.join(self.auth_hook_dir, 'telegram_code')),
        )
        logging.getLogger('debug').debug({'mode': 'telegram', 'action': 'started'})

    @retry(retry=retry_if_exception_type(Exception), stop=stop_after_attempt(20), wait=wait_fixed(10))
    async def fast_start(self):
        logging.getLogger('debug').debug({'mode': 'telegram', 'action': 'fast_start'})
        if not self._telegram_client.is_connected():
            await self._telegram_client.connect()
        await self._telegram_client.sign_in(bot_token=self.bot_token)
        logging.getLogger('debug').debug({'mode': 'telegram', 'action': 'fast_started'})

    def polling_file(self, fname):
        async def f():
            while not os.path.exists(fname):
                await asyncio.sleep(5.0)
            with open(fname, 'r') as code_file:
                return code_file.read().strip()
        return f

    async def stop(self):
        return await self.disconnect()

    def add_event_handler(self, *args, **kwargs):
        return self._telegram_client.add_event_handler(*args, **kwargs)

    def catch_up(self):
        return self._telegram_client.catch_up()

    def delete_messages(self, *args, **kwargs):
        return self._telegram_client.delete_messages(*args, **kwargs)

    def disconnect(self):
        return self._telegram_client.disconnect()

    @property
    def disconnected(self):
        return self._telegram_client.disconnected

    def download_document(self, *args, **kwargs):
        return self._telegram_client._download_document(
            *args,
            date=datetime.datetime.now(),
            thumb=None,
            progress_callback=None,
            msg_data=None,
            **kwargs,
        )

    async def upload_file(self, file: hints.FileLike, file_name: str = None, cache_key: str = None):
        file_id = await self._telegram_client.upload_file(
            file=file,
            file_name=file_name,
        )
        if cache_key:
            self.file_handle_cache[cache_key] = file_id
        return file_id

    def get_cached_file_id(self, cache_key: str):
        return self.file_handle_cache.get(cache_key, None)

    def edit_message(self, *args, **kwargs):
        return self._telegram_client.edit_message(*args, **kwargs)

    def edit_permissions(self, *args, **kwargs):
        return self._telegram_client.edit_permissions(*args, **kwargs)

    def forward_messages(self, *args, **kwargs):
        return self._telegram_client.forward_messages(*args, **kwargs)

    def get_entity(self, *args, **kwargs):
        return self._telegram_client.get_entity(*args, **kwargs)

    def get_input_entity(self, *args, **kwargs):
        return self._telegram_client.get_input_entity(*args, **kwargs)

    def get_permissions(self, *args, **kwargs):
        return self._telegram_client.get_permissions(*args, **kwargs)

    def iter_admin_log(self, *args, **kwargs):
        return self._telegram_client.iter_admin_log(*args, **kwargs)

    def iter_messages(self, *args, **kwargs):
        return self._telegram_client.iter_messages(*args, **kwargs)

    def list_event_handlers(self):
        return self._telegram_client.list_event_handlers()

    def remove_event_handlers(self):
        for handler in reversed(self.list_event_handlers()):
            self._telegram_client.remove_event_handler(*handler)

    def run_until_disconnected(self):
        return self._telegram_client.run_until_disconnected()

    def send_message(self, *args, **kwargs):
        return self._telegram_client.send_message(*args, **kwargs)

    def send_file(self, *args, **kwargs):
        return self._telegram_client.send_file(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self._telegram_client(*args, **kwargs)

    @property
    def t(self):
        return self._telegram_client


class RequestContext:
    def __init__(self, bot_name, chat, request_id: str = None, request_id_length: int = 12):
        self.bot_name = bot_name
        self.chat = chat
        self.request_id = request_id or RequestContext.generate_request_id(request_id_length)
        self.default_fields = {
            'bot_name': self.bot_name,
            'chat_id': self.chat['chat_id'],
            'request_id': self.request_id,
        }

    @staticmethod
    def generate_request_id(length):
        return generate_request_id(length)

    def add_default_fields(self, **fields):
        self.default_fields.update(fields)

    def statbox(self, **kwargs):
        logging.getLogger('statbox').info(msg={**self.default_fields, **kwargs})

    def debug_log(self, **kwargs):
        logging.getLogger('debug').debug(msg={**self.default_fields, **kwargs})

    def error_log(self, e, level=logging.ERROR, **fields):
        all_fields = {**self.default_fields, **fields}
        error_log(e, level=level, **all_fields)

    def is_group_mode(self):
        return self.chat['chat_id'] < 0

    def is_personal_mode(self):
        return self.chat['chat_id'] > 0

    def personal_buttons(self):
        if self.is_personal_mode():
            return [close_button()]
