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

from ..models import (
    CatalogRequirement,
    CatalogRequirementImport,
    CatalogRequirementOutput,
)
from ..utils.temp_file import copy_upload_to_temp_file, get_temp_file
from ..views.catalog_requirements import (
    CatalogRequirementsView,
    get_catalog_requirement_filters,
    get_catalog_requirement_sort,
)
from .catalog_modules import get_catalog_module_columns
from .common import Column, ColumnGroup
from .handlers import get_export_labels_handler, hide_columns


def get_catalog_requirement_columns(
    catalog_module_columns: ColumnGroup = Depends(get_catalog_module_columns),
) -> ColumnGroup[CatalogRequirementImport, CatalogRequirement]:
    catalog_module_columns.attr_name = "catalog_module"

    return ColumnGroup(
        CatalogRequirementImport,
        "Catalog Requirement",
        [
            catalog_module_columns,
            Column("ID", "id"),
            Column("Reference", "reference"),
            Column("Summary", "summary", required=True),
            Column("Description", "description"),
            Column("GS Absicherung", "gs_absicherung"),
            Column("GS Verantwortliche", "gs_verantwortliche"),
        ],
    )


router = APIRouter()


router.get(
    "/excel/catalog_requirements/column-names",
    summary="Get columns names for catalog requirements Excel export",
    response_model=list[str],
    **CatalogRequirementsView.kwargs
)(get_export_labels_handler(get_catalog_requirement_columns))


@router.get(
    "/excel/catalog_requirements",
    response_class=FileResponse,
    **CatalogRequirementsView.kwargs
)
def download_catalog_requirements_excel(
    catalog_requirements_view: CatalogRequirementsView = Depends(),
    where_clauses=Depends(get_catalog_requirement_filters),
    sort_clauses=Depends(get_catalog_requirement_sort),
    columns: ColumnGroup = Depends(hide_columns(get_catalog_requirement_columns)),
    temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
    sheet_name="Catalog Requirements",
    filename="catalog_requirements.xlsx",
) -> FileResponse:
    catalog_requirements = catalog_requirements_view.list_catalog_requirements(
        where_clauses, sort_clauses
    )
    df = columns.export_to_dataframe(catalog_requirements)
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
    columns: ColumnGroup = Depends(get_catalog_requirement_columns),
    temp_file: NamedTemporaryFile = Depends(copy_upload_to_temp_file),
    dry_run: bool = False,
) -> list[CatalogRequirementOutput]:
    df = pd.read_excel(temp_file, engine="openpyxl")
    catalog_requirement_imports = columns.import_from_dataframe(df)
    list(catalog_requirement_imports)
    return []
