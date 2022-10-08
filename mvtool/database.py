# coding: utf-8
#
# Copyright (C) 2022 Helmar Hutschenreuter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from typing import Type, TypeVar, Generic
from fastapi import Depends, HTTPException
from sqlmodel import create_engine, Session, SQLModel, select
from sqlmodel.sql.expression import Select, SelectOfScalar
from sqlmodel.pool import StaticPool
from .config import DatabaseConfig

# workaround for https://github.com/tiangolo/sqlmodel/issues/189
SelectOfScalar.inherit_cache = True
Select.inherit_cache = True

# configure naming conventions to make migration easier
# see https://alembic.sqlalchemy.org/en/latest/naming.html#the-importance-of-naming-constraints
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
SQLModel.metadata.naming_convention = naming_convention


class __State:
    engine = None


def setup_engine(database_config: DatabaseConfig):
    if __State.engine is None:
        if database_config.url.startswith("sqlite"):
            __State.engine = create_engine(
                database_config.url,
                connect_args={"check_same_thread": False},  # Needed for SQLite
                echo=database_config.echo,
                poolclass=StaticPool,  # Maintain a single connection for all threads
            )
        else:
            __State.engine = create_engine(
                database_config.url,
                echo=database_config.echo,
                pool_pre_ping=True,  # check connections before using them
            )
    return __State.engine


def dispose_engine():
    __State.engine.dispose()
    __State.engine = None


def get_session():
    with Session(__State.engine) as session:
        yield session
        session.commit()


def create_all():
    SQLModel.metadata.create_all(__State.engine)


def drop_all():
    SQLModel.metadata.drop_all(__State.engine)


T = TypeVar("T", bound=SQLModel)


class CRUDOperations(Generic[T]):
    def __init__(self, session=Depends(get_session)):
        self.session = session

    def read_all_from_db(self, sqlmodel: Type[T], **filters) -> list[T]:
        query = select(sqlmodel)

        for key, value in filters.items():
            if value is not None:
                query = query.where(sqlmodel.__dict__[key] == value)
        query = query.order_by(sqlmodel.id)

        return self.session.exec(query).all()

    def create_in_db(self, item: T) -> T:
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def read_from_db(self, sqlmodel: Type[T], id: int) -> T:
        item = self.session.get(sqlmodel, id)
        if item:
            return item
        else:
            item_name = sqlmodel.__name__
            raise HTTPException(404, f"No {item_name} with id={id}.")

    def update_in_db(self, id: int, item_update: T) -> T:
        sqlmodel = item_update.__class__
        item = self.read_from_db(sqlmodel, id)
        item_update.id = item.id
        self.session.merge(item_update)
        self.session.flush()
        return item

    def delete_from_db(self, sqlmodel: Type[T], id: int) -> None:
        item = self.read_from_db(sqlmodel, id)
        self.session.delete(item)
        self.session.flush()
