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


from tempfile import NamedTemporaryFile
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
import pandas as pd
from mvtool.utils.temp_file import copy_upload_to_temp_file, get_temp_file
from mvtool.views.catalog_requirements import (
    get_catalog_requirement_filters,
    get_catalog_requirement_sort,
)

from mvtool.views.requirements import RequirementsView

from ..models import AbstractComplianceInput, Requirement, RequirementOutput
from .catalog_requirements import (
    CatalogRequirementImport,
    get_catalog_requirement_columns_def,
)
from .common import ColumnDef, ColumnsDef


class RequirementImport(AbstractComplianceInput):
    id: int | None = None
    reference: str | None
    summary: str
    description: str | None
    catalog_requirement: CatalogRequirementImport | None
    target_object: str | None
    milestone: str | None


def get_requirement_columns_def(
    catalog_requirement_columns_def: ColumnsDef = Depends(
        get_catalog_requirement_columns_def
    ),
) -> ColumnsDef[RequirementImport, Requirement]:
    catalog_requirement_columns_def.attr_name = "catalog_requirement"

    return ColumnsDef(
        RequirementImport,
        "Requirement",
        [
            catalog_requirement_columns_def,
            ColumnDef("ID", "id"),
            ColumnDef("Reference", "reference"),
            ColumnDef("Summary", "summary", required=True),
            ColumnDef("Description", "description"),
            ColumnDef("Compliance Status", "compliance_status"),
            ColumnDef("Compliance Comment", "compliance_comment"),
            ColumnDef("Target Object", "target_object"),
            ColumnDef("Milestone", "milestone"),
        ],
    )


router = APIRouter()


@router.get(
    "/excel/requirements",
    response_class=FileResponse,
    **RequirementsView.kwargs,
)
def download_requirements_excel(
    requirements_view: RequirementsView = Depends(),
    where_clauses=Depends(get_catalog_requirement_filters),
    sort_clauses=Depends(get_catalog_requirement_sort),
    columns_def: ColumnsDef = Depends(get_requirement_columns_def),
    temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
    sheet_name="Requirements",
    filename="requirements.xlsx",
) -> FileResponse:
    requirements = requirements_view.list_requirements(where_clauses, sort_clauses)
    df = columns_def.export_to_dataframe(requirements)
    df.to_excel(temp_file.name, sheet_name=sheet_name, index=False)
    return FileResponse(temp_file.name, filename=filename)


@router.post(
    "/excel/requirements",
    status_code=201,
    response_model=list[RequirementOutput],
    **RequirementsView.kwargs,
)
def upload_requirements_excel(
    requirements_view: RequirementsView = Depends(),
    columns_def: ColumnsDef = Depends(get_requirement_columns_def),
    temp_file: NamedTemporaryFile = Depends(copy_upload_to_temp_file),
    dry_run: bool = False,
) -> list[RequirementOutput]:
    df = pd.read_excel(temp_file, engine="openpyxl")
    requirement_imports = columns_def.import_from_dataframe(df)
    list(requirement_imports)
    # TODO: validate requirements imports and perform import
    return []
