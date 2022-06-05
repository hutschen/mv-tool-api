# coding: utf-8
# 
# Copyright 2022 Helmar Hutschenreuter
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation. You may obtain
# a copy of the GNU AGPL V3 at https://www.gnu.org/licenses/.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AGPL V3 for more details.  

from typing import TypeVar, Generic
from fastapi import Depends, HTTPException
from sqlmodel import create_engine, Session, SQLModel, select
from sqlmodel.pool import StaticPool

engine = create_engine(
    'sqlite://',
    connect_args={'check_same_thread': False},  # Needed for SQLite
    echo=False,  # Do not log generated SQL
    poolclass=StaticPool
)

def get_session():
    with Session(engine) as session:
        yield session

def create_all():
    SQLModel.metadata.create_all(engine)

def drop_all():
    SQLModel.metadata.drop_all(engine)


T = TypeVar('T', bound=SQLModel)

class CRUDMixin(Generic[T]):
    def _read_all_from_db(self, sqlmodel_) -> list[T]:
        query = select(sqlmodel_)
        return self.session.exec(query).all()

    def _create_in_db(self, item: T) -> T:
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def _read_from_db(self, sqlmodel_, id: int) -> T:
        item = self.session.get(sqlmodel_, id)
        if item:
            return item
        else:
            item_name = item.__class__.__name__
            raise HTTPException(404, f'No {item_name} with id={id}.')

    def _update_in_db(self, id: int, item_update: T) -> T:
        item = self._read_from_db(item_update.__class__, id)
        item_update.id = item.id
        self.session.merge(item_update)
        self.session.commit()
        return item

    def _delete_in_db(self, sqlmodel_, id: int) -> None:
        item = self._read_from_db(sqlmodel_, id)
        self.session.delete(item)
        self.session.commit()