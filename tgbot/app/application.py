import asyncio
import logging
import os
from concurrent.futures import ProcessPoolExecutor

from aiogrobid import GrobidClient
from aiokit import AioRootThing
from izihawa_utils.importlib import import_object
from stc_geck.client import StcGeck

from library.ipfs import IpfsHttpClient
from library.telegram.dynamic_bot_manager import DynamicBotManager
from library.telegram.promotioner import Promotioner
from library.user_manager import UserManager
from tgbot.app.database import Database
from tgbot.app.query_builder import QueryProcessor
from tgbot.promotions import get_promotions


class TelegramApplication(AioRootThing):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.reloading_task = None
        self.long_tasks = set()

        self.database = Database(data_directory=config['application']['data_directory'])
        self.starts.append(self.database)

        is_embed = self.config['summa']['embed'].get('enabled', True)

        self.dynamic_bot_manager = DynamicBotManager(
            data_directory=config['application']['data_directory'],
            database=self.database,
            post_start_hook=lambda bot_config, telegram_client: self.set_handlers(
                telegram_client=telegram_client,
                bot_config=bot_config,
                extra_handlers=[
                    'tgbot.handlers.seed.SeedHandler',
                    'tgbot.handlers.trends.TrendsHelpHandler',
                    'tgbot.handlers.trends.TrendsHandler',
                    'tgbot.handlers.trends.TrendsEditHandler'
                ] if not is_embed else [],
            ),
            pre_stop_hook=lambda bot_name, telegram_client: telegram_client.remove_event_handlers(),
            total_shards=config['application']['workers'],
            default_bot=config['application'].get('default_bot')
        )
        self.starts.append(self.dynamic_bot_manager)
        self.geck = StcGeck(
            ipfs_http_base_url=self.config['ipfs']['http']['base_url'],
            ipfs_data_directory=self.config['summa']['embed']['ipfs_data_directory'],
            index_names=self.config['summa']['embed']['index_names'],
            grpc_api_endpoint=self.config['summa']['endpoint'],
            embed=is_embed,
        )
        self.starts.append(self.geck)
        self.summa_client = self.geck.get_summa_client()

        self.starts.append(self.summa_client)
        self.query_processor = QueryProcessor(self.config['summa']['query_processor']['profile'])

        self.ipfs_http_client = IpfsHttpClient(base_url=config['ipfs']['http']['base_url'], retry_delay=5.0)
        self.starts.append(self.ipfs_http_client)

        self.cloudflare_ipfs_http_client = IpfsHttpClient(base_url='https://cloudflare-ipfs.com', retry_delay=5.0)
        self.starts.append(self.cloudflare_ipfs_http_client)

        self.grobid_client = None
        if (
            'grobid' in self.config
            and self.config['grobid'].get('enabled', True)
            and not self.is_read_only()
        ):
            self.grobid_client = GrobidClient(base_url=config['grobid']['base_url'])
            self.starts.append(self.grobid_client)

        self.metadata_retriever = None
        if (
            'metadata_retriever' in self.config
            and self.config['metadata_retriever'].get('enabled', True)
            and not self.is_read_only()
        ):
            from library.integral.metadata_retriever import MetadataRetriever
            self.metadata_retriever = MetadataRetriever(
                summa_client=self.summa_client,
                config=self.config['metadata_retriever'],
            )
            self.starts.append(self.metadata_retriever)

        self.librarian_service = None
        if (
            'librarian' in self.config
            and self.config['librarian'].get('enabled', True)
        ):
            from tgbot.app.librarian_service import LibrarianService
            self.librarian_service = LibrarianService(
                application=self,
                auth_hook_dir=os.path.join(config['application']['data_directory'], 'auth'),
                data_directory=os.path.join(config['application']['data_directory'], 'librarian'),
                config=config['librarian'],
            )
            self.starts.append(self.librarian_service)

        self.file_flow = None
        if (
            'file_flow' in self.config
            and self.config['file_flow'].get('enabled', True)
            and not self.is_read_only()
        ):
            from library.integral.file_flow import FileFlow
            self.file_flow = FileFlow(
                self.summa_client,
                self.config['file_flow'],
                index_alias='nexus_science',
                pool=ProcessPoolExecutor()
            )
            self.starts.append(self.file_flow)

        self.promotioner = Promotioner(
            promotions=get_promotions(),
            promotion_vars=dict(
                twitter_contact_url=self.config['twitter']['contact_url'],
                related_channel=self.config['telegram']['related_channel'],
            )
        )

        self.user_manager = UserManager()
        self._handlers = []

    async def start(self):
        await self.summa_client.wait_started()
        logging.getLogger('statbox').info({
            'mode': 'application',
            'action': 'started',
        })

    def is_read_only(self):
        return self.config['application'].get('is_read_only', False) or self.geck.embed

    def set_handlers(self, telegram_client, bot_config: dict, extra_handlers=None, extra_warning=None):
        for handler in (
            self.config['telegram']['command_handlers']
            + (extra_handlers or [])
            + self.config['telegram']['search_handlers']
        ):
            import_object(handler)(
                self,
                bot_config=bot_config,
                extra_warning=extra_warning,
            ).register_for(telegram_client, bot_name=bot_config['bot_name'])

    async def stop(self):
        self.dynamic_bot_manager.reloading_task.cancel()
        n = len(self.long_tasks)
        logging.getLogger('debug').debug({
            'action': 'stopping_long_tasks',
            'tasks': n,
        })
        for download in set(self.long_tasks):
            await download.external_cancel()
        await asyncio.gather(*map(lambda x: x.task, self.long_tasks))
        logging.getLogger('debug').debug({
            'action': 'stopped_long_tasks',
            'tasks': n,
        })

    def get_telegram_client(self, bot_name):
        if bot_name in self.dynamic_bot_manager.telegram_clients:
            return self.dynamic_bot_manager.telegram_clients[bot_name]
