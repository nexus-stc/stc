import aiosqlite
from aiokit import AioThing


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class AioSqlite(AioThing):
    def __init__(self, db_name):
        super().__init__()
        self.db = aiosqlite.connect(db_name)

    async def start(self):
        self.db = await self.db
        self.db.row_factory = dict_factory

    def __getattr__(self, item):
        return getattr(self.db, item)
