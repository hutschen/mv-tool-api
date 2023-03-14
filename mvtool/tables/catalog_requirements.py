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

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, constr

from mvtool.models import CatalogRequirement, CatalogRequirementOutput
from mvtool.utils.temp_file import copy_upload_to_temp_file, get_temp_file
from mvtool.views.catalog_requirements import (
    CatalogRequirementsView,
    get_catalog_requirement_filters,
    get_catalog_requirement_sort,
)

from .catalog_modules import CatalogModuleImport, get_catalog_module_columns_def
from .common import ColumnDef, ColumnsDef


class CatalogRequirementImport(BaseModel):
    id: int | None = None
    reference: str | None
    summary: str
    description: str | None
    gs_absicherung: constr(regex=r"^(B|S|H)$") | None
    gs_verantwortliche: str | None
    catalog_module: CatalogModuleImport | None = None


def get_catalog_requirement_columns_def(
    catalog_module_columns_def: ColumnsDef = Depends(get_catalog_module_columns_def),
) -> ColumnsDef[CatalogRequirementImport, CatalogRequirement]:
    catalog_module_columns_def.attr_name = "catalog_module"

    return ColumnsDef(
        CatalogRequirementImport,
        "Catalog Requirement",
        [
            catalog_module_columns_def,
            ColumnDef("ID", "id"),
            ColumnDef("Reference", "reference"),
            ColumnDef("Summary", "summary", required=True),
            ColumnDef("Description", "description"),
            ColumnDef("GS Absicherung", "gs_absicherung"),
            ColumnDef("GS Verantwortliche", "gs_verantwortliche"),
        ],
    )


router = APIRouter()


@router.get(
    "/excel/catalog_requirements",
    response_class=FileResponse,
    **CatalogRequirementsView.kwargs
)
def download_catalog_requirements_excel(
    catalog_requirements_view: CatalogRequirementsView = Depends(),
    where_clauses=Depends(get_catalog_requirement_filters),
    sort_clauses=Depends(get_catalog_requirement_sort),
    columns_def: ColumnsDef = Depends(get_catalog_requirement_columns_def),
    temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
    sheet_name="Catalog Requirements",
    filename="catalog_requirements.xlsx",
) -> FileResponse:
    catalog_requirements = catalog_requirements_view.list_catalog_requirements(
        where_clauses, sort_clauses
    )
    df = columns_def.export_to_dataframe(catalog_requirements)
    df.to_excel(temp_file.file, sheet_name=sheet_name, index=False)
    return FileResponse(temp_file.name, filename=filename)


@router.post(
    "/excel/catalog_requirements",
    status_code=201,
    response_model=list[CatalogRequirementOutput],
    **CatalogRequirementsView.kwargs
)
def upload_catalog_requirements_excel(
    catalog_requirements_view: CatalogRequirementsView = Depends(),
    columns_def: ColumnsDef = Depends(get_catalog_requirement_columns_def),
    temp_file: NamedTemporaryFile = Depends(copy_upload_to_temp_file),
    dry_run: bool = False,
) -> list[CatalogRequirementOutput]:
    df = pd.read_excel(temp_file, engine="openpyxl")
    catalog_requirement_imports = columns_def.import_from_dataframe(df)
    list(catalog_requirement_imports)
    return []
