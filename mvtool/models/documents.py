# -*- coding: utf-8 -*-
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

from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..db.database import Base
from .common import CommonFieldsMixin, ETagMixin

if TYPE_CHECKING:
    from .projects import ProjectImport, ProjectOutput


class DocumentInput(BaseModel):
    reference: str | None
    title: str
    description: str | None


class DocumentImport(ETagMixin, DocumentInput):
    id: int | None = None
    project: "ProjectImport | None"


class Document(CommonFieldsMixin, Base):
    __tablename__ = "document"
    reference = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True)
    project = relationship("Project", back_populates="documents", lazy="joined")
    measures = relationship("Measure", back_populates="document")


class DocumentRepresentation(BaseModel):
    class Config:
        orm_mode = True

    id: int
    reference: str | None
    title: str


class DocumentOutput(DocumentInput):
    class Config:
        orm_mode = True

    id: int
    project: "ProjectOutput"
