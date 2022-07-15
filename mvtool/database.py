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
from .config import load_config, get_config_filename

def get_engine():
    config = load_config(get_config_filename())
    return create_engine(
        config.sqlite_url,
        connect_args={'check_same_thread': False},  # Needed for SQLite
        echo=config.sqlite_echo,
        poolclass=StaticPool
    )

__engine = get_engine()

def get_session():
    with Session(__engine) as session:
        yield session

def create_all():
    SQLModel.metadata.create_all(__engine)

def drop_all():
    SQLModel.metadata.drop_all(__engine)


T = TypeVar('T', bound=SQLModel)


class CRUDOperations(Generic[T]):
    def __init__(self, session: Session, sqlmodel_: SQLModel):
        self.session = session
        self.sqlmodel = sqlmodel_

    def read_all_from_db(self, **filters) -> list[T]:
        query = select(self.sqlmodel)

        for key, value in filters.items():
            if value is not None:
                query = query.where(self.sqlmodel.__dict__[key] == value)

        return self.session.exec(query).all()

    def create_in_db(self, item: T) -> T:
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def read_from_db(self, id: int) -> T:
        item = self.session.get(self.sqlmodel, id)
        if item:
            return item
        else:
            item_name = item.__class__.__name__
            raise HTTPException(404, f'No {item_name} with id={id}.')

    def update_in_db(self, id: int, item_update: T) -> T:
        item = self.read_from_db(id)
        item_update.id = item.id
        self.session.merge(item_update)
        self.session.commit()
        return item

    def delete_in_db(self, id: int) -> None:
        item = self.read_from_db(id)
        self.session.delete(item)
        self.session.commit()