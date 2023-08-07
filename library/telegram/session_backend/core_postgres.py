from typing import (
    Any,
    Union,
)

from sqlalchemy.dialects.postgresql import insert
from telethon.sessions.memory import _SentFileType
from telethon.tl.types import (
    InputDocument,
    InputPhoto,
)

from .core import AlchemyCoreSession


class AlchemyPostgresCoreSession(AlchemyCoreSession):
    def set_update_state(self, entity_id: int, row: Any) -> None:
        t = self.UpdateState.__table__
        values = dict(pts=row.pts, qts=row.qts, date=row.date.timestamp(),
                      seq=row.seq, unread_count=row.unread_count)
        with self.engine.begin() as conn:
            conn.execute(insert(t)
                         .values(session_id=self.session_id, entity_id=entity_id, **values)
                         .on_conflict_do_update(constraint=t.primary_key, set_=values))

    def process_entities(self, tlo: Any) -> None:
        rows = self._entities_to_rows(tlo)
        if not rows:
            return

        t = self.Entity.__table__
        ins = insert(t)
        upsert = ins.on_conflict_do_update(constraint=t.primary_key, set_={
            "hash": ins.excluded.hash,
            "username": ins.excluded.username,
            "phone": ins.excluded.phone,
            "name": ins.excluded.name,
        })
        with self.engine.begin() as conn:
            conn.execute(upsert, [dict(session_id=self.session_id, id=row[0], hash=row[1],
                                       username=row[2], phone=row[3], name=row[4])
                                  for row in rows])

    def cache_file(self, md5_digest: str, file_size: int,
                   instance: Union[InputDocument, InputPhoto]) -> None:
        if not isinstance(instance, (InputDocument, InputPhoto)):
            raise TypeError("Cannot cache {} instance".format(type(instance)))

        t = self.SentFile.__table__
        values = dict(id=instance.id, hash=instance.access_hash)
        with self.engine.begin() as conn:
            conn.execute(insert(t)
                         .values(session_id=self.session_id, md5_digest=md5_digest,
                                 type=_SentFileType.from_type(type(instance)).value,
                                 file_size=file_size, **values)
                         .on_conflict_do_update(constraint=t.primary_key, set_=values))
