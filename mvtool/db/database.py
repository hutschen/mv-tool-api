# -*- coding: utf-8 -*-
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

from typing import Type, TypeVar

from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import Session, sessionmaker, registry
from sqlalchemy.pool import StaticPool

from ..config import DatabaseConfig
from ..utils.errors import NotFoundError

mapper_registry = registry()
mapper_registry.metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
Base = mapper_registry.generate_base()


class __State:
    engine: Engine | None = None
    session_local: sessionmaker | None = None


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
            __State.engine = create_engine(  # type: ignore
                database_config.url,
                echo=database_config.echo,
                pool_pre_ping=True,  # check connections before using them
            )

        # Create sessionmaker instance after engine is initialized
        __State.session_local = sessionmaker(
            bind=__State.engine, autocommit=False, autoflush=False
        )

    return __State.engine, __State.session_local


def dispose_connection():
    if __State.engine is None:
        raise RuntimeError("Engine is not initialized")

    __State.engine.dispose()
    __State.engine = None
    __State.session_local = None


# @contextmanager
def get_session():
    if __State.session_local is None:
        raise RuntimeError("sessionmaker is not initialized")

    session: Session = __State.session_local()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all():
    if __State.engine is None:
        raise RuntimeError("Engine is not initialized")

    Base.metadata.create_all(bind=__State.engine)


def drop_all():
    if __State.engine is None:
        raise RuntimeError("Engine is not initialized")

    Base.metadata.drop_all(bind=__State.engine)


T = TypeVar("T", bound=Base)


def create_in_db(session: Session, item: T) -> T:
    session.add(item)
    session.flush()
    session.refresh(item)
    return item


def read_from_db(session: Session, orm_class: Type[T], id: int) -> T:
    item = session.get(orm_class, id)
    if item:
        return item
    else:
        item_name = orm_class.__name__
        raise NotFoundError(f"No {item_name} with id={id}.")


def delete_from_db(session: Session, item: T, skip_flush: bool = False) -> None:
    session.delete(item)
    if not skip_flush:
        session.flush()
