import datetime
from typing import (
    Any,
    Optional,
    Tuple,
    Union,
)

from sqlalchemy import (
    and_,
    select,
)
from sqlalchemy.dialects.postgresql import insert
from telethon import utils
from telethon.crypto import AuthKey
from telethon.sessions.memory import _SentFileType
from telethon.tl.types import (
    InputDocument,
    InputPhoto,
    PeerChannel,
    PeerChat,
    PeerUser,
    updates,
)

from .orm import AlchemySession


class AlchemyCoreSession(AlchemySession):
    def _load_session(self) -> None:
        t = self.Session.__table__
        rows = self.engine.execute(select([t.c.dc_id, t.c.server_address, t.c.port, t.c.auth_key])
                                   .where(t.c.session_id == self.session_id))
        try:
            self._dc_id, self._server_address, self._port, auth_key = next(rows)
            self._auth_key = AuthKey(data=auth_key)
        except StopIteration:
            pass

    def _get_auth_key(self) -> Optional[AuthKey]:
        t = self.Session.__table__
        rows = self.engine.execute(select([t.c.auth_key]).where(t.c.session_id == self.session_id))
        try:
            ak = next(rows)[0]
        except (StopIteration, IndexError):
            ak = None
        return AuthKey(data=ak) if ak else None

    def get_update_state(self, entity_id: int) -> Optional[updates.State]:
        t = self.UpdateState.__table__
        rows = self.engine.execute(select([t])
                                   .where(and_(t.c.session_id == self.session_id,
                                               t.c.entity_id == entity_id)))
        try:
            _, _, pts, qts, date, seq, unread_count = next(rows)
            date = datetime.datetime.utcfromtimestamp(date)
            return updates.State(pts, qts, date, seq, unread_count)
        except StopIteration:
            return None

    def set_update_state(self, entity_id: int, row: Any) -> None:
        t = self.UpdateState.__table__
        self.engine.execute(t.delete().where(and_(t.c.session_id == self.session_id,
                                                  t.c.entity_id == entity_id)))
        self.engine.execute(t.insert()
                            .values(session_id=self.session_id, entity_id=entity_id, pts=row.pts,
                                    qts=row.qts, date=row.date.timestamp(), seq=row.seq,
                                    unread_count=row.unread_count))

    def _update_session_table(self) -> None:
        with self.engine.begin() as conn:
            insert_stmt = insert(self.Session.__table__)
            conn.execute(
                insert_stmt.on_conflict_do_update(
                    index_elements=['session_id', 'dc_id'],
                    set_={
                        'session_id': insert_stmt.excluded.session_id,
                        'dc_id': insert_stmt.excluded.dc_id,
                        'server_address': insert_stmt.excluded.server_address,
                        'port': insert_stmt.excluded.port,
                        'auth_key': insert_stmt.excluded.auth_key,
                    }
                ),
                session_id=self.session_id, dc_id=self._dc_id,
                server_address=self._server_address, port=self._port,
                auth_key=(self._auth_key.key if self._auth_key else b'')
            )

    def save(self) -> None:
        # engine.execute() autocommits
        pass

    def delete(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(self.Session.__table__.delete().where(
                self.Session.__table__.c.session_id == self.session_id))
            conn.execute(self.Entity.__table__.delete().where(
                self.Entity.__table__.c.session_id == self.session_id))
            conn.execute(self.SentFile.__table__.delete().where(
                self.SentFile.__table__.c.session_id == self.session_id))
            conn.execute(self.UpdateState.__table__.delete().where(
                self.UpdateState.__table__.c.session_id == self.session_id))

    def _entity_values_to_row(self, id: int, hash: int, username: str, phone: str, name: str
                              ) -> Any:
        return id, hash, username, phone, name

    def process_entities(self, tlo: Any) -> None:
        rows = self._entities_to_rows(tlo)
        if not rows:
            return

        t = self.Entity.__table__
        with self.engine.begin() as conn:
            conn.execute(t.delete().where(and_(t.c.session_id == self.session_id,
                                               t.c.id.in_([row[0] for row in rows]))))
            conn.execute(t.insert(), [dict(session_id=self.session_id, id=row[0], hash=row[1],
                                           username=row[2], phone=row[3], name=row[4])
                                      for row in rows])

    def get_entity_rows_by_phone(self, key: str) -> Optional[Tuple[int, int]]:
        return self._get_entity_rows_by_condition(self.Entity.__table__.c.phone == key)

    def get_entity_rows_by_username(self, key: str) -> Optional[Tuple[int, int]]:
        return self._get_entity_rows_by_condition(self.Entity.__table__.c.username == key)

    def get_entity_rows_by_name(self, key: str) -> Optional[Tuple[int, int]]:
        return self._get_entity_rows_by_condition(self.Entity.__table__.c.name == key)

    def _get_entity_rows_by_condition(self, condition) -> Optional[Tuple[int, int]]:
        t = self.Entity.__table__
        rows = self.engine.execute(select([t.c.id, t.c.hash])
                                   .where(and_(t.c.session_id == self.session_id, condition)))
        try:
            return next(rows)
        except StopIteration:
            return None

    def get_entity_rows_by_id(self, key: int, exact: bool = True) -> Optional[Tuple[int, int]]:
        t = self.Entity.__table__
        if exact:
            rows = self.engine.execute(select([t.c.id, t.c.hash]).where(
                and_(t.c.session_id == self.session_id, t.c.id == key)))
        else:
            ids = (
                utils.get_peer_id(PeerUser(key)),
                utils.get_peer_id(PeerChat(key)),
                utils.get_peer_id(PeerChannel(key))
            )
            rows = self.engine.execute(select([t.c.id, t.c.hash]).where(
                and_(t.c.session_id == self.session_id, t.c.id.in_(ids)))
            )

        try:
            return next(rows)
        except StopIteration:
            return None

    def get_file(self, md5_digest: str, file_size: int, cls: Any) -> Optional[Tuple[int, int]]:
        t = self.SentFile.__table__
        rows = (self.engine.execute(select([t.c.id, t.c.hash])
                                    .where(and_(t.c.session_id == self.session_id,
                                                t.c.md5_digest == md5_digest,
                                                t.c.file_size == file_size,
                                                t.c.type == _SentFileType.from_type(cls).value))))
        try:
            return next(rows)
        except StopIteration:
            return None

    def cache_file(self, md5_digest: str, file_size: int,
                   instance: Union[InputDocument, InputPhoto]) -> None:
        if not isinstance(instance, (InputDocument, InputPhoto)):
            raise TypeError("Cannot cache {} instance".format(type(instance)))

        t = self.SentFile.__table__
        file_type = _SentFileType.from_type(type(instance)).value
        with self.engine.begin() as conn:
            conn.execute(t.delete().where(session_id=self.session_id, md5_digest=md5_digest,
                                          type=file_type, file_size=file_size))
            conn.execute(t.insert().values(session_id=self.session_id, md5_digest=md5_digest,
                                           type=file_type, file_size=file_size, id=instance.id,
                                           hash=instance.access_hash))
