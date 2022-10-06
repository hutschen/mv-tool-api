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
import sqlalchemy as sa
from pytest_alembic import MigrationContext
from pytest_alembic.tests import (
    test_single_head_revision,
    test_upgrade,
    test_up_down_consistency,
    test_model_definitions_match_ddl,
)
from mvtool.migration import migrate, get_alembic_config


@pytest.fixture
def alembic_config(config):
    return get_alembic_config(config.database)


def test_migrate(config):
    migrate(config.database)


def test_migrate_52864629f869_add_common_fields(
    alembic_runner: MigrationContext, alembic_engine: sa.engine.Engine
):
    alembic_runner.migrate_up_before("52864629f869")
    alembic_runner.insert_into("project", {"id": 1, "name": "test"})
    alembic_runner.insert_into(
        "requirement", {"id": 1, "summary": "test", "project_id": 1}
    )
    alembic_runner.insert_into(
        "measure", {"id": 1, "summary": "test", "requirement_id": 1, "completed": False}
    )
    alembic_runner.insert_into("document", {"id": 1, "title": "test", "project_id": 1})
    alembic_runner.migrate_up_one()

    # check project has a timestamp
    with alembic_engine.connect() as conn:
        project = conn.execute(
            sa.select(["*"]).select_from(sa.table("project"))
        ).fetchone()
        assert project["created"] is not None
        assert project["updated"] is not None
