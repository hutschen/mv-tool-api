# coding: utf-8
#
# Copyright (C) 2023 Helmar Hutschenreuter
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


from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from .common import CommonFieldsMixin, ETagMixin
from .measures import Measure

if TYPE_CHECKING:
    from .projects import Project, ProjectImport, ProjectOutput


class DocumentInput(SQLModel):
    reference: str | None
    title: str
    description: str | None


class DocumentImport(ETagMixin, DocumentInput):
    id: int | None = None
    project: "ProjectImport | None"


class Document(CommonFieldsMixin, table=True):
    reference: str | None
    title: str
    description: str | None
    project_id: int | None = Field(default=None, foreign_key="project.id")
    project: "Project" = Relationship(
        back_populates="documents", sa_relationship_kwargs=dict(lazy="joined")
    )
    measures: list[Measure] = Relationship(back_populates="document")


class DocumentRepresentation(SQLModel):
    id: int
    reference: str | None
    title: str


class DocumentOutput(DocumentInput):
    id: int
    project: "ProjectOutput"
