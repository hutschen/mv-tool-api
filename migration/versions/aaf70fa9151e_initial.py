"""initial

Revision ID: aaf70fa9151e
Revises: 
Create Date: 2022-09-27 18:29:35.242338

"""
from alembic import op
import sqlalchemy as sa
from sqlmodel.sql.sqltypes import AutoString


# revision identifiers, used by Alembic.
revision = "aaf70fa9151e"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "gs_baustein",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference", AutoString(), nullable=False),
        sa.Column("title", AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "project",
        sa.Column("name", AutoString(), nullable=False),
        sa.Column("description", AutoString(), nullable=True),
        sa.Column("jira_project_id", AutoString(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "document",
        sa.Column("reference", AutoString(), nullable=True),
        sa.Column("title", AutoString(), nullable=False),
        sa.Column("description", AutoString(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], "fk_document_project"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "requirement",
        sa.Column("reference", AutoString(), nullable=True),
        sa.Column("summary", AutoString(), nullable=False),
        sa.Column("description", AutoString(), nullable=True),
        sa.Column("target_object", AutoString(), nullable=True),
        sa.Column("compliance_status", AutoString(), nullable=True),
        sa.Column("compliance_comment", AutoString(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("gs_anforderung_reference", AutoString(), nullable=True),
        sa.Column("gs_absicherung", AutoString(), nullable=True),
        sa.Column("gs_verantwortliche", AutoString(), nullable=True),
        sa.Column("gs_baustein_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["gs_baustein_id"], ["gs_baustein.id"], "fk_requirement_gs_baustein"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["project.id"], "fk_requirement_project"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "measure",
        sa.Column("summary", AutoString(), nullable=False),
        sa.Column("description", AutoString(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("jira_issue_id", AutoString(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"], ["document.id"], "fk_measure_document"
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"], ["requirement.id"], "fk_measure_requirement"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("measure")
    op.drop_table("requirement")
    op.drop_table("document")
    op.drop_table("project")
    op.drop_table("gs_baustein")
    # ### end Alembic commands ###