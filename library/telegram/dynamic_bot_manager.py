import asyncio
import logging
import os
import traceback

from aiokit import AioThing

from .base import BaseTelegramClient


class MultipleAsyncExecution:
    def __init__(self, par):
        self.par = par
        self.s = asyncio.Semaphore(par)

    async def execute(self, coro):
        if not self.s:
            raise RuntimeError('`ParallelAsyncExecution` has been already joined')
        await self.s.acquire()
        task = asyncio.create_task(coro)
        task.add_done_callback(lambda f: self.s.release())
        return task

    async def join(self):
        for i in range(self.par):
            await self.s.acquire()
        s = self.s
        self.s = None
        for i in range(self.par):
            s.release()


class DynamicBotManager(AioThing):
    priority_bots = {
        'SciJournalClubBot',
        'science_nexus_bot',
        'SciArticleNexus_Bot',
        'asschandmustdie_bot',
        'Nexus_books_moji_bot',
        'nexus_search_brian_bot',
        'FtutorNexusBot',
        'MyLibgenBot',
    }

    def __init__(
        self,
        data_directory,
        database,
        polling_interval=600,
        post_start_hook=None,
        pre_stop_hook=None,
        total_shards=None,
        default_bot=None,
    ):
        super().__init__()
        self.data_directory = data_directory
        self.database = database
        self.polling_interval = polling_interval
        self.post_start_hook = post_start_hook
        self.pre_stop_hook = pre_stop_hook
        self.telegram_clients = {}
        self.reloading_task = None
        self.total_shards = total_shards
        self.default_bot = default_bot

    async def start(self):
        if self.default_bot:
            await self.database.add_new_bot(
                bot_name=self.default_bot['bot_name'],
                bot_token=self.default_bot['bot_token'],
                user_id=0,
            )
            await self.database.set_bot_credentials(
                bot_name=self.default_bot['bot_name'],
                app_id=self.default_bot['app_id'],
                app_hash=self.default_bot['app_hash'],
            )
        self.reloading_task = asyncio.create_task(self.reload_bots())

    async def stop(self):
        if self.reloading_task:
            self.reloading_task.cancel()
            logging.getLogger('debug').debug({
                'action': 'waiting_reloading_task',
                'mode': 'dynamic_bot',
            })
            await self.reloading_task
        for bot_name in list(self.telegram_clients.keys()):
            await self.stop_bot(bot_name=bot_name)

    def session_database_for_bot(self, bot_name):
        return {'session_id': os.path.join(self.data_directory, bot_name + '.sdb')}

    def clean_bot_session(self, bot_name):
        try:
            os.remove(self.session_database_for_bot(bot_name)['session_id'] + '.session')
        except FileNotFoundError:
            pass
        try:
            os.remove(self.session_database_for_bot(bot_name)['session_id'] + '.session-journal')
        except FileNotFoundError:
            pass

    async def start_bot(self, target_bots_configs, bot_name):
        bot_config = target_bots_configs[bot_name]
        try:
            logging.getLogger('debug').debug({
                'action': 'start',
                'mode': 'dynamic_bot',
                'bot_name': bot_name,
            })
            self.telegram_clients[bot_name] = BaseTelegramClient(
                app_id=bot_config.get('app_id'),
                app_hash=bot_config.get('app_hash'),
                bot_token=bot_config['bot_token'],
                database=self.session_database_for_bot(bot_name),
                proxy_config=bot_config.get('mtproxy') or None,
            )
            await self.telegram_clients[bot_name].start()
            if self.post_start_hook:
                self.post_start_hook(bot_config, self.telegram_clients[bot_name])
            logging.getLogger('debug').debug({
                'action': 'started',
                'mode': 'dynamic_bot',
                'bot_name': bot_name,
            })
        except Exception as e:
            logging.getLogger('error').error({
                'action': 'error',
                'mode': 'dynamic_bot',
                'bot_name': bot_name,
                'error': str(e),
            })
            if 'Bot token expired' in str(e) or 'Your API ID or Hash cannot be empty or None' in str(e):
                await self.database.bots_db_wrapper.db.execute('update user_bots set is_deleted = true where bot_name = ?', (bot_name,))

            del target_bots_configs[bot_name]
            self.clean_bot_session(bot_name=bot_name)

    async def stop_bot(self, bot_name):
        logging.getLogger('debug').debug({
            'action': 'stop',
            'mode': 'dynamic_bot',
            'bot_name': bot_name,
        })
        if bot_name not in self.telegram_clients:
            return

        if self.pre_stop_hook:
            self.pre_stop_hook(bot_name, self.telegram_clients[bot_name])
        try:
            await self.telegram_clients[bot_name].stop()
        except Exception:
            pass
        del self.telegram_clients[bot_name]

    async def reload_bots(self):
        while True:
            logging.getLogger('debug').info({
                'action': 'reload',
                'mode': 'dynamic_bot',
            })
            try:
                target_bots = {}
                async with self.database.bots_db_wrapper.db.execute("""
                select bot_name, bot_token,
                is_reload_required, app_id, app_hash, mtproxy, owner_id
                from user_bots
                where is_deleted = false
                """) as cursor:
                    async for row in cursor:
                        target_bots[row['bot_name']] = row
                logging.getLogger('debug').debug({
                    'action': 'reload',
                    'mode': 'dynamic_bot',
                    'bots': len(target_bots)
                })
                ready_bots = []
                for ready_session_file in os.listdir(self.data_directory):
                    if ready_session_file.endswith('.sdb.session'):
                        ready_bot = ready_session_file
                        if ready_session_file.endswith('.sdb.session'):
                            ready_bot = ready_session_file[:-len('.sdb.session')]
                        if ready_bot in self.telegram_clients:
                            continue
                        if ready_bot in target_bots:
                            ready_bots.append(ready_bot)
                        else:
                            self.clean_bot_session(bot_name=ready_bot)
                for target_bot_name in target_bots:
                    if target_bots[target_bot_name]['is_reload_required']:
                        await self.stop_bot(target_bot_name)
                        await self.database.bots_db_wrapper.db.execute(
                            'update user_bots set is_reload_required = false where bot_name = ?', (target_bot_name,)
                        )

                launch_list = ready_bots + list(set(target_bots.keys()).difference(self.telegram_clients.keys()).difference(ready_bots))
                launch_list = list(sorted(launch_list, key=lambda x: 0 if x in self.priority_bots else 1))

                executor = MultipleAsyncExecution(self.total_shards)
                for new_bot_name in launch_list:
                    logging.getLogger('debug').debug({
                        'action': 'reload',
                        'mode': 'dynamic_bot',
                        'bots': new_bot_name
                    })
                    await executor.execute(self.start_bot(target_bots_configs=target_bots, bot_name=new_bot_name))
                await executor.join()

                for removed_bot in set(self.telegram_clients.keys()).difference(target_bots.keys()):
                    await self.stop_bot(removed_bot)
                    self.clean_bot_session(bot_name=removed_bot)
                logging.getLogger('debug').debug({
                    'action': 'polling',
                    'mode': 'dynamic_bot',
                })
                await asyncio.sleep(self.polling_interval)
            except asyncio.CancelledError:
                logging.getLogger('debug').debug({
                    'action': 'reload_task_cancelled',
                    'mode': 'dynamic_bot',
                })
                break
            except Exception as e:
                logging.getLogger('error').error({
                    'action': 'error',
                    'mode': 'dynamic_bot',
                    'error': str(e),
                })
                traceback.print_exc()
