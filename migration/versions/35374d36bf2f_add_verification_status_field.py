"""add verification status field

Revision ID: 35374d36bf2f
Revises: c083b27f9c47
Create Date: 2023-03-04 14:39:56.711992

"""
from alembic import op
import sqlalchemy as sa
from sqlmodel.sql.sqltypes import AutoString


# revision identifiers, used by Alembic.
revision = "35374d36bf2f"
down_revision = "c083b27f9c47"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # create verification_status column in measure table
    with op.batch_alter_table("measure", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("verification_status", AutoString(), nullable=True)
        )

    # copy data from verified to verification_status where verified is true
    op.execute(
        """
        UPDATE measure
        SET verification_status = 'verified'
        WHERE verified = true
        """
    )

    # remove verified column from measure table
    with op.batch_alter_table("measure", schema=None) as batch_op:
        batch_op.drop_column("verified")


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("measure", schema=None) as batch_op:
        batch_op.add_column(sa.Column("verified", sa.BOOLEAN(), nullable=False))
        batch_op.drop_column("verification_status")

    # ### end Alembic commands ###