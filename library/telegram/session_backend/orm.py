import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Tuple,
    Union,
)

from sqlalchemy import orm
from telethon import utils
from telethon.crypto import AuthKey
from telethon.sessions.memory import (
    MemorySession,
    _SentFileType,
)
from telethon.tl.types import (
    InputDocument,
    InputPhoto,
    PeerChannel,
    PeerChat,
    PeerUser,
    updates,
)

if TYPE_CHECKING:
    from .sqlalchemy import AlchemySessionContainer


class AlchemySession(MemorySession):
    def __init__(self, container: 'AlchemySessionContainer', session_id: str) -> None:
        super().__init__()
        self.container = container
        self.db = container.db
        self.engine = container.db_engine
        self.Version, self.Session, self.Entity, self.SentFile, self.UpdateState = (
            container.Version, container.Session, container.Entity,
            container.SentFile, container.UpdateState)
        self.session_id = session_id
        self._load_session()

    def _load_session(self) -> None:
        sessions = self._db_query(self.Session).all()
        session = sessions[0] if sessions else None
        if session:
            self._dc_id = session.dc_id
            self._server_address = session.server_address
            self._port = session.port
            self._auth_key = AuthKey(data=session.auth_key)

    def clone(self, to_instance=None) -> MemorySession:
        return super().clone(MemorySession())

    def _get_auth_key(self) -> Optional[AuthKey]:
        sessions = self._db_query(self.Session).all()
        session = sessions[0] if sessions else None
        if session and session.auth_key:
            return AuthKey(data=session.auth_key)
        return None

    def set_dc(self, dc_id: str, server_address: str, port: int) -> None:
        super().set_dc(dc_id, server_address, port)
        self._update_session_table()
        self._auth_key = self._get_auth_key()

    def get_update_state(self, entity_id: int) -> Optional[updates.State]:
        row = self.UpdateState.query.get((self.session_id, entity_id))
        if row:
            date = datetime.datetime.utcfromtimestamp(row.date)
            return updates.State(row.pts, row.qts, date, row.seq, row.unread_count)
        return None

    def set_update_state(self, entity_id: int, row: Any) -> None:
        if row:
            self.db.merge(self.UpdateState(session_id=self.session_id, entity_id=entity_id,
                                           pts=row.pts, qts=row.qts, date=row.date.timestamp(),
                                           seq=row.seq,
                                           unread_count=row.unread_count))
            self.save()

    @MemorySession.auth_key.setter
    def auth_key(self, value: AuthKey) -> None:
        self._auth_key = value
        self._update_session_table()

    def _update_session_table(self) -> None:
        self.Session.query.filter(self.Session.session_id == self.session_id).delete()
        self.db.add(self.Session(session_id=self.session_id, dc_id=self._dc_id,
                                 server_address=self._server_address, port=self._port,
                                 auth_key=(self._auth_key.key if self._auth_key else b'')))

    def _db_query(self, dbclass: Any, *args: Any) -> orm.Query:
        return dbclass.query.filter(
            dbclass.session_id == self.session_id, *args
        )

    def save(self) -> None:
        self.container.save()

    def close(self) -> None:
        # Nothing to do here, connection is managed by AlchemySessionContainer.
        pass

    def delete(self) -> None:
        self._db_query(self.Session).delete()
        self._db_query(self.Entity).delete()
        self._db_query(self.SentFile).delete()
        self._db_query(self.UpdateState).delete()

    def _entity_values_to_row(self, id: int, hash: int, username: str, phone: str, name: str
                              ) -> Any:
        return self.Entity(session_id=self.session_id, id=id, hash=hash,
                           username=username, phone=phone, name=name)

    def process_entities(self, tlo: Any) -> None:
        rows = self._entities_to_rows(tlo)
        if not rows:
            return

        for row in rows:
            self.db.merge(row)
        self.save()

    def get_entity_rows_by_phone(self, key: str) -> Optional[Tuple[int, int]]:
        row = self._db_query(self.Entity,
                             self.Entity.phone == key).one_or_none()
        return (row.id, row.hash) if row else None

    def get_entity_rows_by_username(self, key: str) -> Optional[Tuple[int, int]]:
        row = self._db_query(self.Entity,
                             self.Entity.username == key).one_or_none()
        return (row.id, row.hash) if row else None

    def get_entity_rows_by_name(self, key: str) -> Optional[Tuple[int, int]]:
        row = self._db_query(self.Entity,
                             self.Entity.name == key).one_or_none()
        return (row.id, row.hash) if row else None

    def get_entity_rows_by_id(self, key: int, exact: bool = True) -> Optional[Tuple[int, int]]:
        if exact:
            query = self._db_query(self.Entity, self.Entity.id == key)
        else:
            ids = (
                utils.get_peer_id(PeerUser(key)),
                utils.get_peer_id(PeerChat(key)),
                utils.get_peer_id(PeerChannel(key))
            )
            query = self._db_query(self.Entity, self.Entity.id.in_(ids))

        row = query.one_or_none()
        return (row.id, row.hash) if row else None

    def get_file(self, md5_digest: str, file_size: int, cls: Any) -> Optional[Tuple[int, int]]:
        row = self._db_query(self.SentFile,
                             self.SentFile.md5_digest == md5_digest,
                             self.SentFile.file_size == file_size,
                             self.SentFile.type == _SentFileType.from_type(
                                 cls).value).one_or_none()
        return (row.id, row.hash) if row else None

    def cache_file(self, md5_digest: str, file_size: int,
                   instance: Union[InputDocument, InputPhoto]) -> None:
        if not isinstance(instance, (InputDocument, InputPhoto)):
            raise TypeError("Cannot cache {} instance".format(type(instance)))

        self.db.merge(
            self.SentFile(session_id=self.session_id, md5_digest=md5_digest, file_size=file_size,
                          type=_SentFileType.from_type(type(instance)).value,
                          id=instance.id, hash=instance.access_hash))
        self.save()
