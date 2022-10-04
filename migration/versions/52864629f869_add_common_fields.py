"""add common fields

Revision ID: 52864629f869
Revises: aaf70fa9151e
Create Date: 2022-10-04 20:06:54.945859

"""
from datetime import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy import table, column
from sqlalchemy.exc import OperationalError


# revision identifiers, used by Alembic.
revision = "52864629f869"
down_revision = "aaf70fa9151e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table_names = ["requirement", "project", "measure", "gs_baustein", "document"]
    for table_name in table_names:
        # add columns: created, updated
        op.add_column(table_name, sa.Column("created", sa.DateTime(), nullable=True))
        op.add_column(table_name, sa.Column("updated", sa.DateTime(), nullable=True))

        # set default values for created, updated
        table_ = table(table_name, column("created"), column("updated"))
        op.execute(
            table_.update().values(created=datetime.now(), updated=datetime.now())
        )

        # set not null constraint for columns: created, updated
        try:
            op.alter_column(table_name, "created", nullable=False)
            op.alter_column(table_name, "updated", nullable=False)
        except OperationalError:
            # sqlite does not support altering columns
            pass


def downgrade() -> None:
    table_names = ["requirement", "project", "measure", "gs_baustein", "document"]
    for table_name in table_names:
        op.drop_column(table_name, "created")
        op.drop_column(table_name, "updated")
