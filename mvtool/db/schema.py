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

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func, or_, select
from sqlalchemy.orm import Session, relationship

from ..models.jira_ import JiraIssue
from .database import Base


class CommonFieldsMixin:
    id = Column(Integer, primary_key=True, autoincrement=True)
    created = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
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


class Project(CommonFieldsMixin, Base):
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

    @property
    def _compliant_count_query(self):
        return (
            select([func.count()])
            .select_from(Requirement)
            .outerjoin(Measure)
            .where(
                Requirement.project_id == self.id,
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

    @property
    def completion_progress(self):
        session = Session.object_session(self)

        # get the total number of measures in project
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of completed measures in project
        completed_query = self._compliant_count_query.where(
            Measure.completion_status == "completed"
        )
        completed = session.execute(completed_query).scalar()

        return completed / total if total else None

    @property
    def verification_progress(self):
        session = Session.object_session(self)

        # get the total number of measures in project
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of verified measures in project
        verified_query = self._compliant_count_query.where(
            Measure.verification_status == "verified"
        )
        verified = session.execute(verified_query).scalar()

        return verified / total if total else None


class Requirement(CommonFieldsMixin, Base):
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
        compliance_query = select([Measure.compliance_status]).where(
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

    @property
    def _compliant_count_query(self):
        return (
            select([func.count()])
            .select_from(Measure)
            .where(
                Measure.requirement_id == self.id,
                or_(
                    Measure.compliance_status.in_(("C", "PC")),
                    Measure.compliance_status.is_(None),
                ),
            )
        )

    @property
    def completion_progress(self) -> float | None:
        if self.compliance_status not in ("C", "PC", None):
            return None

        session = Session.object_session(self)

        # get the total number of measures subordinated to this requirement
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of completed measures subordinated to this requirement
        completed_query = self._compliant_count_query.where(
            Measure.completion_status == "completed"
        )
        completed = session.execute(completed_query).scalar()

        return completed / total if total else 0.0

    @property
    def verification_progress(self) -> float | None:
        if self.compliance_status not in ("C", "PC", None):
            return None

        session = Session.object_session(self)

        # get the total number of measures subordinated to this requirement
        total = session.execute(self._compliant_count_query).scalar()

        # get the number of verified measures subordinated to this requirement
        verified_query = self._compliant_count_query.where(
            Measure.verification_status == "verified"
        )
        verified = session.execute(verified_query).scalar()

        return verified / total if total else 0.0


class Document(CommonFieldsMixin, Base):
    __tablename__ = "document"
    reference = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True)
    project = relationship("Project", back_populates="documents", lazy="joined")
    measures = relationship("Measure", back_populates="document")


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
