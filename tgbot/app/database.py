import logging
import os
import time

from aiokit import AioThing

from tgbot.app.aiosqlite_wrapper import AioSqlite


class Database(AioThing):
    def __init__(self, data_directory):
        super().__init__()
        self.bots_db_wrapper = AioSqlite(os.path.join(data_directory, "bots.db"))
        self.starts.append(self.bots_db_wrapper)

        self.users_db_wrapper = AioSqlite(os.path.join(data_directory, "users.db"))
        self.starts.append(self.users_db_wrapper)

    async def start(self):
        await self.init_db()

    async def init_db(self):
        await self.bots_db_wrapper.db.execute("""
            CREATE TABLE IF NOT EXISTS user_bots (
                bot_name text unique,
                bot_token text,
                is_reload_required boolean,
                is_deleted boolean default 0,
                created_at integer,
                app_id text,
                app_hash text,
                owner_id bigint,
                mtproxy text
            );
        """)

        await self.bots_db_wrapper.db.execute("""
            CREATE TABLE IF NOT EXISTS telegram_files (
                bot_name text,
                cid text,
                file_id text
            );
        """)

        await self.bots_db_wrapper.db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS telegram_files_bot_name_cid_ix
            ON telegram_files(bot_name, cid);
        """)

        await self.users_db_wrapper.db.execute("""
            CREATE TABLE IF NOT EXISTS uploads (
                user_id bigint,
                message_id bigint,
                doi text
            );
        """)

        await self.users_db_wrapper.db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                bot_name text,
                chat_id bigint,
                doi text
            );
        """)

        await self.users_db_wrapper.db.execute("""
            CREATE TABLE IF NOT EXISTS upload_approves (
                message_id bigint,
                decision bigint
            );
        """)

        await self.users_db_wrapper.db.execute("""
            CREATE TABLE IF NOT EXISTS file_votes (
                bot_name text,
                user_id bigint,
                doi text,
                cid text,
                vote bigint
            );
        """)
        await self.users_db_wrapper.db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS file_votes_bot_name_user_id_cid
            ON file_votes(bot_name, user_id, cid);
        """)

    async def get_cached_file(self, bot_name, cid):
        async with self.bots_db_wrapper.db.execute("""
        select file_id from telegram_files where bot_name = ? and cid = ?
        """, (bot_name, cid)) as cursor:
            async for row in cursor:
                return row['file_id']

    async def put_cached_file(self, bot_name, cid, file_id):
        await self.bots_db_wrapper.db.execute("""
        INSERT OR IGNORE into telegram_files(bot_name, cid, file_id) VALUES (?, ?, ?)
        """, (bot_name, cid, file_id))
        await self.bots_db_wrapper.db.commit()

    async def delete_cached_file(self, cid):
        logging.getLogger('statbox').info({
            'action': 'delete_cached_file',
            'mode': 'telegram',
            'cid': cid,
        })
        await self.bots_db_wrapper.db.execute("""
        delete from telegram_files where cid = ?
        """, (cid,))
        await self.bots_db_wrapper.db.commit()

    async def add_upload(self, user_id, message_id, internal_id):
        await self.users_db_wrapper.db.execute("""
        INSERT OR IGNORE into uploads(user_id, message_id, doi) VALUES (?, ?, ?)
        """, (user_id, message_id, internal_id))
        await self.users_db_wrapper.db.commit()

    async def add_approve(self, message_id, decision):
        await self.users_db_wrapper.db.execute("""
        INSERT OR IGNORE into upload_approves(message_id, decision) VALUES (?, ?)
        """, (message_id, decision))
        await self.users_db_wrapper.db.commit()

    async def add_vote_broken_file(self, bot_name, user_id, internal_id, cid, reason):
        await self.users_db_wrapper.db.execute("""
        INSERT OR IGNORE into file_votes(bot_name, user_id, doi, cid, vote) VALUES (?, ?, ?, ?, ?)
        """, (bot_name, user_id, internal_id, cid, -1))
        await self.users_db_wrapper.db.commit()

    async def add_new_bot(self, bot_name, bot_token, user_id: int):
        await self.bots_db_wrapper.db.execute("""
            insert into
            user_bots(bot_name, bot_token, owner_id, created_at, is_deleted)
            values (?, ?, ?, ?, ?)
            on conflict(bot_name) do update
            set bot_token = EXCLUDED.bot_token,
            is_deleted = true,
            is_reload_required = true,
            owner_id = EXCLUDED.owner_id
        """, (
            bot_name,
            bot_token,
            user_id,
            int(time.time()),
            False
        ))
        await self.bots_db_wrapper.db.commit()

    async def set_bot_credentials(self, bot_name: str, app_id: str, app_hash: str):
        await self.bots_db_wrapper.db.execute(
            "update user_bots set is_deleted = false, "
            "is_reload_required = true, app_id = ?, app_hash = ? where bot_name = ?",
            (app_id, app_hash, bot_name,),
        )
        await self.bots_db_wrapper.db.commit()
