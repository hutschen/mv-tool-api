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

from datetime import datetime
import pytest
import sqlalchemy as sa
from pytest_alembic import MigrationContext
from pytest_alembic.tests import (
    test_single_head_revision,
    test_upgrade,
    test_up_down_consistency,
    test_model_definitions_match_ddl,
)
from mvtool.config import Config
from mvtool.migration import migrate, get_alembic_config


@pytest.fixture
def alembic_config(config):
    return get_alembic_config(config.database)


def test_migrate_from_before_version_0_5_0(
    config: Config, alembic_runner: MigrationContext, alembic_engine: sa.engine.Engine
):
    alembic_runner.migrate_up_to("aaf70fa9151e")
    with alembic_engine.connect() as conn:
        conn.execute("DROP TABLE alembic_version")
    migrate(config.database)


def test_migrate_from_empty_database(config: Config, alembic_runner: MigrationContext):
    migrate(config.database)
    test_model_definitions_match_ddl(alembic_runner)


def test_migrate_4757e455dd37_apply_naming_conventions(
    alembic_runner: MigrationContext, alembic_engine: sa.engine.Engine
):
    alembic_runner.migrate_up_before("4757e455dd37")
    alembic_runner.migrate_up_one()

    # check names of foreign key constraints
    inspector = sa.inspect(alembic_engine)
    for table_name in ("gs_baustein", "project", "document", "requirement", "measure"):
        for fk in inspector.get_foreign_keys(table_name):
            expected_name = "fk_%s_%s_%s" % (
                table_name,
                fk["constrained_columns"][0],
                fk["referred_table"],
            )
            assert fk["name"] == expected_name

        pk = inspector.get_pk_constraint(table_name)
        expected_name = "pk_%s" % table_name
        assert pk["name"] == expected_name


def test_migrate_52864629f869_add_common_fields(
    alembic_runner: MigrationContext, alembic_engine: sa.engine.Engine
):
    alembic_runner.migrate_up_before("52864629f869")
    alembic_runner.insert_into(
        "project",
        {
            "id": 1,
            "name": "test",
        },
    )
    alembic_runner.insert_into(
        "requirement",
        {
            "id": 1,
            "summary": "test",
            "project_id": 1,
        },
    )
    alembic_runner.insert_into(
        "measure",
        {
            "id": 1,
            "summary": "test",
            "requirement_id": 1,
            "completed": False,
        },
    )
    alembic_runner.insert_into(
        "document",
        {
            "id": 1,
            "title": "test",
            "project_id": 1,
        },
    )
    alembic_runner.migrate_up_one()

    # check project has a timestamp
    with alembic_engine.connect() as conn:
        for table_name in ("project", "requirement", "measure", "document"):
            row = conn.execute(f"SELECT * FROM {table_name}").fetchone()
            assert row["created"] is not None
            assert row["updated"] is not None


def test_migrate_ad9f6e7bc41b_add_catalog_module(
    alembic_runner: MigrationContext, alembic_engine: sa.engine.Engine
):
    gs_baustein_id = 42
    timestamp = datetime.utcnow()
    alembic_runner.migrate_up_before("ad9f6e7bc41b")
    alembic_runner.insert_into(
        "project",
        {
            "id": 1,
            "created": timestamp,
            "updated": timestamp,
            "name": "test",
        },
    )
    alembic_runner.insert_into(
        "gs_baustein",
        {
            "id": gs_baustein_id,
            "created": timestamp,
            "updated": timestamp,
            "title": "test_title",
            "reference": "test_referece",
        },
    )
    alembic_runner.insert_into(
        "requirement",
        {
            "id": 1,
            "created": timestamp,
            "updated": timestamp,
            "summary": "test",
            "project_id": 1,
            "gs_baustein_id": gs_baustein_id,
        },
    )
    alembic_runner.migrate_up_one()

    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")
    with alembic_engine.connect() as conn:
        # check if catalog_module exists
        catalog_module = conn.execute("SELECT * FROM catalog_module").fetchone()
        assert catalog_module["created"] == timestamp_str
        assert catalog_module["updated"] == timestamp_str
        assert catalog_module["title"] == "test_title"
        assert catalog_module["gs_reference"] == "test_referece"

        # check if requirement references catalog_module
        requirement = conn.execute("SELECT * FROM requirement").fetchone()
        assert requirement["catalog_module_id"] == gs_baustein_id
        with pytest.raises(sa.exc.NoSuchColumnError):
            requirement["gs_baustein_id"]


def test_migration_ab13bba14886_add_catalog(
    alembic_runner: MigrationContext, alembic_engine: sa.engine.Engine
):
    timestamp = datetime.utcnow()
    catalog_module_ids = list(range(1, 5))
    alembic_runner.migrate_up_before("ab13bba14886")
    for catalog_module_id in catalog_module_ids:
        alembic_runner.insert_into(
            "catalog_module",
            {
                "id": catalog_module_id,
                "created": timestamp,
                "updated": timestamp,
                "title": "title %d" % catalog_module_id,
            },
        )
    alembic_runner.migrate_up_one()

    # check if default catalog exists
    with alembic_engine.connect() as conn:
        catalog = conn.execute("SELECT * FROM catalog").fetchone()
        catalog_id = catalog["id"]
        assert isinstance(catalog_id, int)
        assert isinstance(catalog["created"], str)
        assert isinstance(catalog["updated"], str)
        assert isinstance(catalog["title"], str)

        # check if catalog links catalog_module
        assert conn.execute(
            "SELECT COUNT(*) FROM catalog_module WHERE catalog_id IS %d" % catalog_id
        ).scalar() == len(catalog_module_ids)
