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
    for table_name in ["requirement", "project", "measure", "gs_baustein", "document"]:
        # add columns with nullable=True
        op.add_column(table_name, sa.Column("created", sa.DateTime(), nullable=True))
        op.add_column(table_name, sa.Column("updated", sa.DateTime(), nullable=True))

        # set values for columns: created, updated
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        op.execute(
            f"""
            UPDATE {table_name} SET created = '{now_str}', updated = '{now_str}'
            """
        )

        # make columns not nullable
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.alter_column("created", nullable=False)
            batch_op.alter_column("updated", nullable=False)


def downgrade() -> None:
    table_names = ["requirement", "project", "measure", "gs_baustein", "document"]
    for table_name in table_names:
        op.drop_column(table_name, "created")
        op.drop_column(table_name, "updated")
