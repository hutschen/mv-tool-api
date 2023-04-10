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
from sqlmodel import Session

from ..database import get_session
from ..models.catalog_requirements import (
    CatalogRequirement,
    CatalogRequirementImport,
    CatalogRequirementOutput,
)
from ..utils.temp_file import copy_upload_to_temp_file, get_temp_file
from ..handlers.catalog_modules import CatalogModules
from ..handlers.catalog_requirements import (
    CatalogRequirements,
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


router = APIRouter(tags=["catalog-requirement"])


router.get(
    "/excel/catalog-requirements/column-names",
    summary="Get columns names for catalog requirements Excel export",
    response_model=list[str],
)(get_export_labels_handler(get_catalog_requirement_columns))


@router.get("/excel/catalog-requirements", response_class=FileResponse)
def download_catalog_requirements_excel(
    catalog_requirements_view: CatalogRequirements = Depends(),
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
    "/excel/catalog-requirements",
    status_code=201,
    response_model=list[CatalogRequirementOutput],
)
def upload_catalog_requirements_excel(
    fallback_catalog_module_id: int | None = None,
    catalog_modules_view: CatalogModules = Depends(),
    catalog_requirements_view: CatalogRequirements = Depends(),
    columns: ColumnGroup = Depends(get_catalog_requirement_columns),
    temp_file: NamedTemporaryFile = Depends(copy_upload_to_temp_file),
    skip_blanks: bool = False,  # skip blank cells
    dry_run: bool = False,  # don't save to database
    session: Session = Depends(get_session),
) -> list[CatalogRequirement]:
    fallback_catalog_module = (
        catalog_modules_view.get_catalog_module(fallback_catalog_module_id)
        if fallback_catalog_module_id is not None
        else None
    )

    # Create data frame from uploaded file
    df = pd.read_excel(temp_file, engine="openpyxl")
    df.drop_duplicates(keep="last", inplace=True)

    # Import data frame into database
    catalog_requirement_imports = columns.import_from_dataframe(
        df, skip_nan=skip_blanks
    )
    catalog_requirements = list(
        catalog_requirements_view.bulk_create_update_catalog_requirements(
            catalog_requirement_imports,
            fallback_catalog_module,
            patch=True,
            skip_flush=dry_run,
        )
    )

    # Rollback if dry run
    if dry_run:
        session.rollback()
        return []
    return catalog_requirements
