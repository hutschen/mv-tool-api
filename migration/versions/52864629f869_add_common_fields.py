"""add common fields

Revision ID: 52864629f869
Revises: aaf70fa9151e
Create Date: 2022-10-04 20:06:54.945859

"""
from datetime import datetime
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "52864629f869"
down_revision = "aaf70fa9151e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table_names = ["requirement", "project", "measure", "gs_baustein", "document"]
    for table_name in table_names:
        # check if table is empty
        row_count = (
            op.get_bind()
            .execute(sa.select([sa.func.count()]).select_from(sa.table(table_name)))
            .scalar()
        )
        if row_count == 0:
            # table is empty, add columns with nullable=False
            op.add_column(
                table_name, sa.Column("created", sa.DateTime(), nullable=False)
            )
            op.add_column(
                table_name, sa.Column("updated", sa.DateTime(), nullable=False)
            )

        else:
            # table is not empty, add columns with nullable=True
            op.add_column(
                table_name, sa.Column("created", sa.DateTime(), nullable=True)
            )
            op.add_column(
                table_name, sa.Column("updated", sa.DateTime(), nullable=True)
            )

            # set default values for columns: created, updated
            op.execute(
                sa.table(table_name, sa.column("created"), sa.column("updated"))
                .update()
                .values(created=datetime.now(), updated=datetime.now())
            )

            # set not null constraint for columns: created, updated
            if op.get_bind().engine.name != "sqlite":
                # sqlite does not support altering columns
                op.alter_column(table_name, "created", nullable=False)
                op.alter_column(table_name, "updated", nullable=False)


def downgrade() -> None:
    table_names = ["requirement", "project", "measure", "gs_baustein", "document"]
    for table_name in table_names:
        op.drop_column(table_name, "created")
        op.drop_column(table_name, "updated")
