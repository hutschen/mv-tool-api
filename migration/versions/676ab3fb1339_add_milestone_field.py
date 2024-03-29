"""add milestone field

Revision ID: 676ab3fb1339
Revises: ba56d996e585
Create Date: 2022-12-20 15:05:59.807348

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "676ab3fb1339"
down_revision = "ba56d996e585"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("requirement", schema=None) as batch_op:
        batch_op.add_column(sa.Column("milestone", sa.String(), nullable=True))


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("requirement", schema=None) as batch_op:
        batch_op.drop_column("milestone")

    # ### end Alembic commands ###
