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
from fastapi import Depends
from sqlmodel import create_engine, Session, SQLModel, select
from sqlmodel.sql.expression import Select, SelectOfScalar
from sqlmodel.pool import StaticPool

from .utils.errors import NotFoundError
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


def setup_connection(database_config: DatabaseConfig):
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


def dispose_connection():
    __State.engine.dispose()
    __State.engine = None


def get_session():
    session = Session(__State.engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all():
    SQLModel.metadata.create_all(__State.engine)


def drop_all():
    SQLModel.metadata.drop_all(__State.engine)


T = TypeVar("T", bound=SQLModel)


def create_in_db(session: Session, item: T) -> T:
    session.add(item)
    session.flush()
    session.refresh(item)
    return item


def read_from_db(session: Session, sqlmodel: Type[T], id: int) -> T:
    item = session.get(sqlmodel, id)
    if item:
        return item
    else:
        item_name = sqlmodel.__name__
        raise NotFoundError(f"No {item_name} with id={id}.")


def delete_from_db(session: Session, item: T, skip_flush: bool = False) -> None:
    session.delete(item)
    if not skip_flush:
        session.flush()
