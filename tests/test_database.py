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

import pytest
from fastapi import HTTPException
from mvtool.database import CRUDOperations, create_all, dispose_engine, drop_all, get_session, setup_engine
from sqlmodel import SQLModel, Field


class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str


def test_setup_engine(config):
    engine = setup_engine(config)
    assert engine is not None

    engine_2 = setup_engine(config)
    assert engine is engine_2
    dispose_engine()


def test_session_commit(config):
    setup_engine(config)
    create_all()

    for session in get_session():
        crud = CRUDOperations(session)
        item = Item(name='test')
        crud.create_in_db(item)
        item_id = item.id

    for session in get_session():
        crud = CRUDOperations(session)
        item = crud.read_from_db(Item, item_id)
        assert item.name == 'test'

    drop_all()
    dispose_engine()

def test_session_rollback(config):
    setup_engine(config)
    create_all()

    # create a new item and rollback the session by raising an exception
    with pytest.raises(Exception) as error_info:
        for session in get_session():
            crud = CRUDOperations(session)
            item = Item(name='test')
            crud.create_in_db(item)
            item_id = item.id
            raise Exception('rollback')
    assert 'rollback' in str(error_info.value)

    # ensure that the item is not in the database
    for session in get_session():
        crud = CRUDOperations(session)
        with pytest.raises(HTTPException):
            crud.read_from_db(Item, item_id)

    drop_all()
    dispose_engine()