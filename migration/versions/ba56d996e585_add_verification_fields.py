"""add verification fields

Revision ID: ba56d996e585
Revises: f94ba991ae4e
Create Date: 2022-12-20 13:34:10.810265

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ba56d996e585"
down_revision = "f94ba991ae4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("measure", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("verification_method", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("verification_comment", sa.String(), nullable=True)
        )


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("measure", schema=None) as batch_op:
        batch_op.drop_column("verification_comment")
        batch_op.drop_column("verification_method")

    # ### end Alembic commands ###
