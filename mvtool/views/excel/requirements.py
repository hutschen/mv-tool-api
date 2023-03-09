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

from fastapi import APIRouter, Depends, UploadFile
from fastapi_utils.cbv import cbv
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlmodel import Session, select
from tempfile import NamedTemporaryFile
from typing import Any, Iterator

from ... import errors
from ...database import get_session
from ...models import Requirement, RequirementInput, RequirementOutput
from ...utils import get_temp_file
from ..projects import ProjectsView
from ..requirements import (
    RequirementsView,
    get_requirement_filters,
    get_requirement_sort,
)
from .catalog_requirements import (
    convert_catalog_requirement_to_row,
    get_catalog_requirement_excel_headers,
)
from .common import ExcelHeader, ExcelView, IdModel
from .projects import convert_project_to_row, get_project_excel_headers

router = APIRouter()


def get_requirement_excel_headers(
    project_headers=Depends(get_project_excel_headers),
    catalog_requirement_headers=Depends(get_catalog_requirement_excel_headers),
) -> list[ExcelHeader]:
    return [
        *project_headers,
        *catalog_requirement_headers,
        ExcelHeader("Requirement ID", optional=True),
        ExcelHeader("Requirement Reference", optional=True),
        ExcelHeader("Requirement Summary"),
        ExcelHeader("Requirement Description", optional=True),
        ExcelHeader("Requirement GS Absicherung", ExcelHeader.WRITE_ONLY, True),
        ExcelHeader("Requirement GS Verantwortliche", ExcelHeader.WRITE_ONLY, True),
        ExcelHeader("Requirement Compliance Status", optional=True),
        ExcelHeader("Requirement Compliance Comment", optional=True),
        ExcelHeader("Requirement Completion Progress", ExcelHeader.WRITE_ONLY, True),
        ExcelHeader("Requirement Verification Progress", ExcelHeader.WRITE_ONLY, True),
        ExcelHeader("Milestone", optional=True),
        ExcelHeader("Target Object", optional=True),
    ]


def convert_requirement_to_row(requirement: Requirement) -> dict[str, Any]:
    return {
        **convert_project_to_row(requirement.project),
        **convert_catalog_requirement_to_row(requirement.catalog_requirement),
        "Requirement ID": requirement.id,
        "Requirement Reference": requirement.reference,
        "Requirement Summary": requirement.summary,
        "Requirement Description": requirement.description,
        "Requirement GS Absicherung": (
            requirement.catalog_requirement.gs_absicherung
            if requirement.catalog_requirement
            else None
        ),
        "Requirement GS Verantwortliche": (
            requirement.catalog_requirement.gs_verantwortliche
            if requirement.catalog_requirement
            else None
        ),
        "Requirement Compliance Status": requirement.compliance_status,
        "Requirement Compliance Comment": requirement.compliance_comment,
        "Requirement Completion Progress": requirement.completion_progress,
        "Requirement Verification Progress": requirement.verification_progress,
        "Target Object": requirement.target_object,
        "Milestone": requirement.milestone,
    }


@cbv(router)
class RequirementsExcelView(ExcelView):
    kwargs = dict(tags=["excel"])

    def __init__(
        self,
        session: Session = Depends(get_session),
        projects: ProjectsView = Depends(ProjectsView),
        requirements: RequirementsView = Depends(RequirementsView),
        headers=Depends(get_requirement_excel_headers),
    ):
        ExcelView.__init__(
            self,
            headers,
        )
        self._session = session
        self._projects = projects
        self._requirements = requirements

    def _convert_to_row(self, data: Requirement) -> dict[str, str]:
        return convert_requirement_to_row(data)

    @router.get(
        "/excel/requirements",
        response_class=FileResponse,
        **kwargs,
    )
    def download_requirements_excel(
        self,
        where_clauses=Depends(get_requirement_filters),
        order_by_clauses=Depends(get_requirement_sort),
        temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
        sheet_name: str = "Reqirements",
        filename: str = "requirements.xlsx",
    ) -> FileResponse:
        return self._process_download(
            self._requirements.list_requirements(where_clauses, order_by_clauses),
            temp_file,
            sheet_name=sheet_name,
            filename=filename,
        )

    def _convert_from_row(
        self, row: dict[str, str], worksheet, row_no: int
    ) -> tuple[int | None, RequirementInput]:
        try:
            requirement_id = IdModel(id=row["ID"]).id
            requirement_input = RequirementInput(
                reference=row["Reference"] or None,
                summary=row["Summary"],
                description=row["Description"] or None,
                target_object=row["Target Object"] or None,
                milestone=row["Milestone"] or None,
                compliance_status=row["Compliance Status"] or None,
                compliance_comment=row["Compliance Comment"] or None,
            )
        except ValidationError as error:
            detail = 'Invalid data on worksheet "%s" at row %d: %s' % (
                worksheet.title,
                row_no + 1,
                error,
            )
            raise errors.ValueHttpError(detail)
        else:
            return requirement_id, requirement_input

    def _bulk_create_patch_requirements(
        self, project_id: int, data: Iterator[tuple[int | None, RequirementInput]]
    ) -> list[Requirement]:
        # Get project from database and retrieve data
        project = self._projects.get_project(project_id)
        data = list(data)

        # Read requirements to be updated from database
        query = select(Requirement).where(
            Requirement.id.in_({id for id, _ in data if id is not None}),
            Requirement.project_id == project_id,
        )
        read_requirements = dict((r.id, r) for r in self._session.exec(query).all())

        # Create or update requirements
        written_requirements = []
        for requirement_id, requirement_input in data:
            if requirement_id is None:
                # Create requirement
                requirement = Requirement.from_orm(requirement_input)
                requirement.project = project
            else:
                # Update requirement
                requirement = read_requirements.get(requirement_id)
                if requirement is None:
                    raise errors.NotFoundError(
                        "Requirement with ID %d not part of project with ID %d"
                        % (requirement_id, project_id)
                    )
                for key, value in requirement_input.dict(exclude_unset=True).items():
                    setattr(requirement, key, value)

            self._requirements._set_jira_project(requirement)
            self._session.add(requirement)
            written_requirements.append(requirement)

        self._session.flush()
        return written_requirements

    @router.post(
        "/projects/{project_id}/requirements/excel",
        status_code=201,
        response_model=list[RequirementOutput],
        **kwargs,
    )
    def upload_requirements_excel(
        self,
        project_id: int,
        upload_file: UploadFile,
        temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
    ) -> Iterator[Requirement]:
        return self._bulk_create_patch_requirements(
            project_id, self._process_upload(upload_file, temp_file)
        )
