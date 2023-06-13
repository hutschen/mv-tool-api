# coding: utf-8
#
# Copyright (C) 2022 Helmar Hutschenreuter
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


from typing import Any, Iterable, Iterator

from fastapi import Depends
from sqlalchemy import Column, func
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select, select

from ..database import delete_from_db, get_session, read_from_db
from ..handlers.documents import Documents
from ..handlers.jira_ import JiraIssues
from ..models.catalog_modules import CatalogModule
from ..models.catalog_requirements import CatalogRequirement
from ..models.catalogs import Catalog
from ..models.documents import Document
from ..models.measures import Measure, MeasureImport, MeasureInput
from ..models.requirements import Requirement
from ..utils.errors import NotFoundError
from ..utils.etag_map import get_from_etag_map
from ..utils.fallback import fallback
from ..utils.filtering import filter_for_existence
from ..utils.iteration import CachedIterable
from ..utils.models import field_is_set
from .requirements import Requirements


class Measures:
    def __init__(
        self,
        jira_issues: JiraIssues = Depends(JiraIssues),
        requirements: Requirements = Depends(Requirements),
        documents: Documents = Depends(Documents),
        session: Session = Depends(get_session),
    ):
        self._jira_issues = jira_issues
        self._requirements = requirements
        self._documents = documents
        self.session = session

    @staticmethod
    def _modify_measures_query(
        query: Select,
        where_clauses: Any = None,
        order_by_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Select:
        """Modify a query to include all required joins, clauses and offset and limit."""
        query = (
            query.join(Requirement)
            .outerjoin(Document)
            .outerjoin(CatalogRequirement)
            .outerjoin(CatalogModule)
            .outerjoin(Catalog)
        )
        if where_clauses:
            query = query.where(*where_clauses)
        if order_by_clauses:
            query = query.order_by(*order_by_clauses)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query

    def list_measures(
        self,
        where_clauses: Any = None,
        order_by_clauses: Any = None,
        offset: int | None = None,
        limit: int | None = None,
        query_jira: bool = True,
    ) -> list[Measure]:
        # construct measures query
        query = self._modify_measures_query(
            select(Measure),
            where_clauses,
            order_by_clauses or [Measure.id],
            offset,
            limit,
        )

        # execute measures query
        measures = self.session.execute(query).scalars().all()

        # set jira project and issue on measures
        if query_jira:
            jira_issue_ids = set()
            for measure in measures:
                if measure.jira_issue_id is not None:
                    jira_issue_ids.add(measure.jira_issue_id)
                self._set_jira_issue(measure, try_to_get=False)
                self._set_jira_project(measure)

            # cache jira issues and return measures
            list(self._jira_issues.get_jira_issues(jira_issue_ids))
        return measures

    def count_measures(self, where_clauses: Any = None) -> int:
        query = self._modify_measures_query(
            select([func.count()]).select_from(Measure), where_clauses
        )
        return self.session.execute(query).scalar()

    def list_measure_values(
        self,
        column: Column,
        where_clauses: list[Any] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        query = self._modify_measures_query(
            select([func.distinct(column)]).select_from(Measure),
            [filter_for_existence(column), *(where_clauses or [])],
            offset=offset,
            limit=limit,
        )
        return self.session.execute(query).scalars().all()

    def count_measure_values(
        self, column: Column, where_clauses: list[Any] | None = None
    ) -> int:
        query = self._modify_measures_query(
            select([func.count(func.distinct(column))]).select_from(Measure),
            [filter_for_existence(column), *(where_clauses or [])],
        )
        return self.session.execute(query).scalar()

    def create_measure(
        self,
        requirement: Requirement,
        creation: MeasureInput | MeasureImport,
        skip_flush: bool = False,
    ) -> Measure:
        measure = Measure(
            **creation.dict(exclude={"id", "requirement", "jira_issue", "document"})
        )
        measure.requirement = requirement

        # check ids of dependencies
        try_to_get_jira_issue = True
        if isinstance(creation, MeasureInput):
            measure.document = self._documents.check_document_id(creation.document_id)
            self._jira_issues.check_jira_issue_id(creation.jira_issue_id)
            try_to_get_jira_issue = False

        self.session.add(measure)
        if not skip_flush:
            self.session.flush()

        self._set_jira_issue(measure, try_to_get=try_to_get_jira_issue)
        return measure

    def get_measure(self, measure_id: int) -> Measure:
        measure = read_from_db(self.session, Measure, measure_id)
        self._set_jira_issue(measure)
        self._set_jira_project(measure)
        return measure

    def update_measure(
        self,
        measure: Measure,
        update: MeasureInput | MeasureImport,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> None:
        # check ids of dependencies
        try_to_get_jira_issue = True
        if isinstance(update, MeasureInput):
            measure.document = self._documents.check_document_id(update.document_id)
            if update.jira_issue_id != measure.jira_issue_id:
                self._jira_issues.check_jira_issue_id(update.jira_issue_id)
                try_to_get_jira_issue = False

        # update measure
        for key, value in update.dict(
            exclude_unset=patch, exclude={"id", "requirement", "jira_issue", "document"}
        ).items():
            setattr(measure, key, value)

        # flush changes
        if not skip_flush:
            self.session.flush()

        self._set_jira_issue(measure, try_to_get=try_to_get_jira_issue)

    def delete_measure(self, measure: Measure, skip_flush: bool = False) -> None:
        return delete_from_db(self.session, measure, skip_flush)

    def bulk_create_update_measures(
        self,
        measure_imports: Iterable[MeasureImport],
        fallback_requirement: Requirement | None = None,
        fallback_catalog_module: CatalogModule | None = None,
        patch: bool = False,
        skip_flush: bool = False,
    ) -> Iterator[Measure]:
        measure_imports = CachedIterable(measure_imports)
        fallback_project = (
            fallback_requirement.project if fallback_requirement else None
        )

        # Convert requirement imports to requirements
        requirements_map = self._requirements.convert_requirement_imports(
            (m.requirement for m in measure_imports if m.requirement is not None),
            fallback_project,
            fallback_catalog_module,
            patch=patch,
        )

        # Convert document imports to documents
        documents_map = self._documents.convert_document_imports(
            (m.document for m in measure_imports if m.document is not None),
            fallback_project,
            patch=patch,
        )

        # Cache jira issues
        jira_issues_map = {
            ji.key: ji
            for ji in self._jira_issues.get_jira_issues(
                {m.jira_issue.key for m in measure_imports if m.jira_issue is not None}
            )
        }

        # Get measures to be updated from the database
        ids = {m.id for m in measure_imports if m.id is not None}
        measures_to_update = {
            m.id: m for m in (self.list_measures([Measure.id.in_(ids)]) if ids else [])
        }

        # Create or update measures
        for measure_import in measure_imports:
            requirement = get_from_etag_map(
                requirements_map, measure_import.requirement
            )

            if measure_import.id is None:
                # Create measure
                measure = self.create_measure(
                    fallback(
                        requirement,
                        fallback_requirement,
                        "No fallback requirement provided.",
                    ),
                    measure_import,
                    skip_flush=True,
                )
            else:
                # Update measure
                measure = measures_to_update.get(measure_import.id)
                if measure is None:
                    raise NotFoundError(f"No measure with id={measure_import.id}.")
                self.update_measure(
                    measure,
                    measure_import,
                    patch=patch,
                    skip_flush=True,
                )

            # Set document
            if field_is_set(measure_import, "document") or not patch:
                measure.document = get_from_etag_map(
                    documents_map, measure_import.document
                )

            # Set jira issue
            if field_is_set(measure_import, "jira_issue") or not patch:
                jira_issue = None
                if measure_import.jira_issue is not None:
                    jira_issue = jira_issues_map.get(measure_import.jira_issue.key)
                    if jira_issue is None:
                        raise NotFoundError(
                            f"No Jira issue with key={measure_import.jira_issue.key}."
                        )
                measure.jira_issue_id = jira_issue.id if jira_issue else None

            yield measure

        if not skip_flush:
            self.session.flush()

    def _set_jira_project(self, measure: Measure, try_to_get: bool = True) -> None:
        self._requirements._set_jira_project(measure.requirement, try_to_get)
        if measure.document is not None:
            self._documents._set_jira_project(measure.document, try_to_get)

    def _set_jira_issue(self, measure: Measure, try_to_get: bool = True) -> None:
        measure._get_jira_issue = (
            lambda jira_issue_id: self._jira_issues.lookup_jira_issue(
                jira_issue_id, try_to_get
            )
        )
