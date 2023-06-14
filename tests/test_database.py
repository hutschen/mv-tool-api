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

import pytest
from fastapi import HTTPException

from mvtool.db.database import (
    create_all,
    create_in_db,
    dispose_connection,
    drop_all,
    get_session,
    read_from_db,
    setup_connection,
)
from mvtool.models import Project


def test_setup_engine(config):
    engine = setup_connection(config.database)
    assert engine is not None

    engine_2 = setup_connection(config.database)
    assert engine is engine_2
    dispose_connection()


def test_session_commit(config):
    setup_connection(config.database)
    create_all()

    for session in get_session():
        item = Project(name="test")
        create_in_db(session, item)
        item_id = item.id

    for session in get_session():
        item = read_from_db(session, Project, item_id)
        assert item.name == "test"

    drop_all()
    dispose_connection()


def test_session_rollback(config):
    setup_connection(config.database)
    create_all()

    # create a new item and rollback the session by raising an exception
    with pytest.raises(Exception) as error_info:
        for session in get_session():
            item = Project(name="test")
            create_in_db(session, item)
            item_id = item.id
            raise Exception("rollback")
    assert "rollback" in str(error_info.value)

    # ensure that the item is not in the database
    for session in get_session():
        with pytest.raises(HTTPException):
            read_from_db(session, Project, item_id)

    drop_all()
    dispose_connection()
