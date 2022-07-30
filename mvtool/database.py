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

from typing import Type, TypeVar, Generic
from fastapi import Depends, HTTPException
from sqlmodel import create_engine, Session, SQLModel, select
from sqlmodel.sql.expression import Select, SelectOfScalar
from sqlmodel.pool import StaticPool
from .config import Config

# workaround for https://github.com/tiangolo/sqlmodel/issues/189
SelectOfScalar.inherit_cache = True
Select.inherit_cache = True

class __State:
    engine = None

def setup_engine(config: Config):
    if __State.engine is None:
        __State.engine = create_engine(
            config.sqlite_url,
            connect_args={'check_same_thread': False},  # Needed for SQLite
            echo=config.sqlite_echo,
            poolclass=StaticPool
        )
    return __State.engine

def dispose_engine():
    __State.engine.dispose()
    __State.engine = None

def get_session():
    with Session(__State.engine) as session:
        return session

def create_all():
    SQLModel.metadata.create_all(__State.engine)

def drop_all():
    SQLModel.metadata.drop_all(__State.engine)


T = TypeVar('T', bound=SQLModel)
class CRUDOperations(Generic[T]):
    def __init__(self, session = Depends(get_session)):
        self.session = session

    def read_all_from_db(self, sqlmodel: Type[T], **filters) -> list[T]:
        query = select(sqlmodel)

        for key, value in filters.items():
            if value is not None:
                query = query.where(sqlmodel.__dict__[key] == value)

        return self.session.exec(query).all()

    def create_in_db(self, item: T) -> T:
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def read_from_db(self, sqlmodel: Type[T], id: int) -> T:
        item = self.session.get(sqlmodel, id)
        if item:
            return item
        else:
            item_name = item.__class__.__name__
            raise HTTPException(404, f'No {item_name} with id={id}.')

    def update_in_db(self, id: int, item_update: T) -> T:
        sqlmodel = item_update.__class__
        item = self.read_from_db(sqlmodel, id)
        item_update.id = item.id
        self.session.merge(item_update)
        self.session.commit()
        return item

    def delete_from_db(self, sqlmodel: Type[T], id: int) -> None:
        item = self.read_from_db(sqlmodel, id)
        self.session.delete(item)
        self.session.commit()