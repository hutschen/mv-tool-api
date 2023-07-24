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

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Select,
    String,
    case,
    func,
    or_,
    select,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Session, relationship

from ..models.jira_ import JiraIssue
from .database import Base


class CommonFieldsMixin:
    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ProgressCountsMixin:
    @staticmethod
    def _get_completion_count_query(id: int | Column) -> Select:
        raise NotImplementedError(
            "_get_completion_count_query must be implemented by subclasses"
        )

    @classmethod
    def _get_completed_count_query(cls, id: int | Column) -> Select:
        return cls._get_completion_count_query(id).where(
            Measure.completion_status == "completed"
        )

    @classmethod
    def _get_verification_count_query(cls, id: int | Column) -> Select:
        return cls._get_completion_count_query(id).where(
            Measure.verification_method.is_not(None)
        )

    @classmethod
    def _get_verified_count_query(cls, id: int | Column) -> Select:
        return cls._get_verification_count_query(id).where(
            Measure.verification_status == "verified"
        )

    @hybrid_property
    def completion_count(self) -> int:
        session = Session.object_session(self)
        return session.execute(self._get_completion_count_query(self.id)).scalar()

    @completion_count.inplace.expression
    @classmethod
    def _completion_count_expression(cls):
        return cls._get_completion_count_query(cls.id).scalar_subquery()

    @hybrid_property
    def completed_count(self) -> int:
        session = Session.object_session(self)
        return session.execute(self._get_completed_count_query(self.id)).scalar()

    @completed_count.inplace.expression
    @classmethod
    def _completed_count_expression(cls):
        return cls._get_completed_count_query(cls.id).scalar_subquery()

    @hybrid_property
    def verification_count(self) -> int:
        session = Session.object_session(self)
        return session.execute(self._get_verification_count_query(self.id)).scalar()

    @verification_count.inplace.expression
    @classmethod
    def _verification_count_expression(cls):
        return cls._get_verification_count_query(cls.id).scalar_subquery()

    @hybrid_property
    def verified_count(self) -> int:
        session = Session.object_session(self)
        return session.execute(self._get_verified_count_query(self.id)).scalar()

    @verified_count.inplace.expression
    @classmethod
    def _verified_count_expression(cls):
        return cls._get_verified_count_query(cls.id).scalar_subquery()

    @hybrid_property
    def completion_progess(self) -> float | None:
        if self.completion_count == 0:
            return None
        return self.completed_count / self.completion_count

    @completion_progess.inplace.expression
    @classmethod
    def _completion_progess_expression(cls):
        return case(
            (cls.completion_count != 0, cls.completed_count / cls.completion_count),
            else_=None,
        )

    @hybrid_property
    def verification_progress(self) -> float | None:
        if self.verification_count == 0:
            return None
        return self.verified_count / self.verification_count

    @verification_progress.inplace.expression
    @classmethod
    def _verification_progress_expression(cls):
        return case(
            (cls.verification_count != 0, cls.verified_count / cls.verification_count),
            else_=None,
        )


class Catalog(CommonFieldsMixin, Base):
    __tablename__ = "catalog"
    reference = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    catalog_modules = relationship(
        "CatalogModule", back_populates="catalog", cascade="all,delete,delete-orphan"
    )


class CatalogModule(CommonFieldsMixin, Base):
    __tablename__ = "catalog_module"
    reference = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    catalog_requirements = relationship(
        "CatalogRequirement",
        back_populates="catalog_module",
        cascade="all,delete,delete-orphan",
    )
    catalog_id = Column(Integer, ForeignKey("catalog.id"), nullable=True)
    catalog = relationship("Catalog", back_populates="catalog_modules", lazy="joined")


class CatalogRequirement(CommonFieldsMixin, Base):
    __tablename__ = "catalog_requirement"
    reference = Column(String, nullable=True)
    summary = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # Special fields for IT Grundschutz Kompendium
    gs_absicherung = Column(String, nullable=True)
    gs_verantwortliche = Column(String, nullable=True)

    catalog_module_id = Column(Integer, ForeignKey("catalog_module.id"), nullable=True)
    catalog_module = relationship(
        "CatalogModule", back_populates="catalog_requirements", lazy="joined"
    )
    requirements = relationship("Requirement", back_populates="catalog_requirement")


class Project(CommonFieldsMixin, ProgressCountsMixin, Base):
    __tablename__ = "project"
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    jira_project_id = Column(String, nullable=True)
    requirements = relationship(
        "Requirement", back_populates="project", cascade="all,delete,delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="project", cascade="all,delete,delete-orphan"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def _get_jira_project(jira_project_id):
            raise NotImplementedError("Getter for JIRA project not set")

        self._get_jira_project = _get_jira_project

    @property
    def jira_project(self):
        if self.jira_project_id is None:
            return None
        return getattr(self, "_get_jira_project")(self.jira_project_id)

    @staticmethod
    def _get_completion_count_query(id: int | Column) -> Select:
        return (
            select(func.count())
            .select_from(Requirement)
            .outerjoin(Measure)
            .where(
                Requirement.project_id == id,
                or_(
                    Requirement.compliance_status.in_(("C", "PC")),
                    Requirement.compliance_status.is_(None),
                ),
                or_(
                    Measure.compliance_status.in_(("C", "PC")),
                    Measure.compliance_status.is_(None),
                ),
            )
        )


class Requirement(CommonFieldsMixin, ProgressCountsMixin, Base):
    __tablename__ = "requirement"
    reference = Column(String, nullable=True)
    summary = Column(String, nullable=False)
    description = Column(String, nullable=True)
    compliance_status = Column(String, nullable=True)
    compliance_comment = Column(String, nullable=True)
    target_object = Column(String, nullable=True)
    milestone = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True)
    project = relationship("Project", back_populates="requirements", lazy="joined")
    catalog_requirement_id = Column(
        Integer, ForeignKey("catalog_requirement.id"), nullable=True
    )
    catalog_requirement = relationship(
        "CatalogRequirement", back_populates="requirements", lazy="joined"
    )
    measures = relationship(
        "Measure", back_populates="requirement", cascade="all,delete,delete-orphan"
    )

    @property
    def compliance_status_hint(self):
        session = Session.object_session(self)

        # get the compliance states of all measures subordinated to this requirement
        compliance_query = select(Measure.compliance_status).where(
            Measure.requirement_id == self.id, Measure.compliance_status != None
        )
        compliance_states = session.execute(compliance_query).scalars().all()

        # compute the compliance status hint
        exists = lambda x: any(x == c in compliance_states for c in compliance_states)
        every = lambda x: all(x == c for c in compliance_states)

        if exists("C") and not (exists("PC") or exists("NC")):
            return "C"
        elif exists("PC") or (exists("C") and exists("NC")):
            return "PC"
        elif exists("NC") and not (exists("C") or exists("PC")):
            return "NC"
        elif every("N/A") and len(compliance_states) > 0:
            return "N/A"
        else:
            return None

    @staticmethod
    def _get_completion_count_query(id: int | Column) -> Select:
        return (
            select(func.count())
            .select_from(Measure)
            .where(
                Measure.requirement_id == id,
                or_(
                    Measure.compliance_status.in_(("C", "PC")),
                    Measure.compliance_status.is_(None),
                ),
            )
        )


class Document(CommonFieldsMixin, ProgressCountsMixin, Base):
    __tablename__ = "document"
    reference = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True)
    project = relationship("Project", back_populates="documents", lazy="joined")
    measures = relationship("Measure", back_populates="document")

    @staticmethod
    def _get_completion_count_query(id: int | Column) -> Select:
        return (
            select(func.count())
            .select_from(Measure)
            .where(
                Measure.document_id == id,
                or_(
                    Measure.compliance_status.in_(("C", "PC")),
                    Measure.compliance_status.is_(None),
                ),
            )
        )


class Measure(CommonFieldsMixin, Base):
    __tablename__ = "measure"
    reference = Column(String, nullable=True)
    summary = Column(String, nullable=False)
    description = Column(String, nullable=True)
    compliance_status = Column(String, nullable=True)
    compliance_comment = Column(String, nullable=True)
    completion_status = Column(String, nullable=True)
    completion_comment = Column(String, nullable=True)
    verification_method = Column(String, nullable=True)
    verification_status = Column(String, nullable=True)
    verification_comment = Column(String, nullable=True)
    jira_issue_id = Column(String, nullable=True)

    requirement_id = Column(Integer, ForeignKey("requirement.id"), nullable=True)
    requirement = relationship("Requirement", back_populates="measures", lazy="joined")
    document_id = Column(Integer, ForeignKey("document.id"), nullable=True)
    document = relationship("Document", back_populates="measures", lazy="joined")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def _get_jira_issue(jira_issue_id):
            raise NotImplementedError("Getter for JIRA issue not set")

        self._get_jira_issue = _get_jira_issue

    @property
    def jira_issue(self) -> JiraIssue | None:
        if self.jira_issue_id is None:
            return None

        return getattr(self, "_get_jira_issue")(self.jira_issue_id)

    @property
    def completion_status_hint(self):
        if self.compliance_status not in ("C", "PC", None):
            return None

        if self.jira_issue and self.jira_issue.status.completed:
            return "completed"
        else:
            return self.completion_status
