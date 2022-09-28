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

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic import command
from sqlalchemy import create_engine, inspect
from .config import load_config

INITIAL_REV = "aaf70fa9151e"
INITIAL_LAYOUT = {
    "document": {"reference", "title", "description", "id", "project_id"},
    "gs_baustein": {"id", "reference", "title"},
    "measure": {
        "summary",
        "description",
        "completed",
        "document_id",
        "id",
        "jira_issue_id",
        "requirement_id",
    },
    "project": {"name", "description", "jira_project_id", "id"},
    "requirement": {
        "reference",
        "summary",
        "description",
        "target_object",
        "compliance_status",
        "compliance_comment",
        "id",
        "project_id",
        "gs_anforderung_reference",
        "gs_absicherung",
        "gs_verantwortliche",
        "gs_baustein_id",
    },
}


def is_initial_revision(engine) -> bool:
    """Checks if the database is at the initial revision.

    This is the case when upgrading from a version before 0.5.0.
    """
    inspector = inspect(engine)
    current_layout = dict()
    for table_name in inspector.get_table_names():
        current_layout[table_name] = {
            c["name"] for c in inspector.get_columns(table_name)
        }
    return current_layout == INITIAL_LAYOUT


def get_current_revision(engine):
    """Returns the current revision of the database."""
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def migrate():
    config = load_config()

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", config.database.url)

    # stamp the database when upgrading from a version before 0.5.0
    engine = create_engine(config.database.url)
    if get_current_revision(engine) is None and is_initial_revision(engine):
        command.stamp(alembic_config, INITIAL_REV)

    # upgrade database to the latest revision
    command.upgrade(alembic_config, "head")
