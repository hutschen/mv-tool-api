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

from typing import Callable

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db.database import get_session
from ..db.schema import CatalogRequirement
from ..handlers.catalog_modules import CatalogModules
from ..handlers.catalog_requirements import (
    CatalogRequirements,
    get_catalog_requirement_filters,
    get_catalog_requirement_sort,
)
from ..models.catalog_requirements import (
    CatalogRequirementImport,
    CatalogRequirementOutput,
)
from .catalog_modules import get_catalog_module_columns
from .columns import Column, ColumnGroup
from .dataframe import DataFrame
from .handlers import (
    get_dataframe_from_uploaded_csv,
    get_dataframe_from_uploaded_excel,
    get_download_csv_handler,
    get_download_excel_handler,
    get_export_labels_handler,
    hide_columns,
)
from .rw_excel import write_excel


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


def _get_catalog_requirements_dataframe(
    catalog_requirements: CatalogRequirements = Depends(),
    where_clauses=Depends(get_catalog_requirement_filters),
    sort_clauses=Depends(get_catalog_requirement_sort),
    columns: ColumnGroup = Depends(hide_columns(get_catalog_requirement_columns)),
) -> DataFrame:
    catalog_requirement_list = catalog_requirements.list_catalog_requirements(
        where_clauses, sort_clauses
    )
    return columns.export_to_dataframe(catalog_requirement_list)


router.get(
    "/excel/catalog-requirements",
    summary="Download catalog requirements as Excel file",
    response_class=FileResponse,
)(
    get_download_excel_handler(
        _get_catalog_requirements_dataframe,
        sheet_name="Catalog Requirements",
        filename="catalog_requirements.xlsx",
    )
)

router.get(
    "/csv/catalog-requirements",
    summary="Download catalog requirements as CSV file",
    response_class=FileResponse,
)(
    get_download_csv_handler(
        _get_catalog_requirements_dataframe,
        filename="catalog_requirements.csv",
    )
)


def _get_upload_catalog_requirements_dataframe_handler(
    get_uploaded_dataframe: Callable,
) -> Callable:
    def upload_catalog_requirements_dataframe(
        fallback_catalog_module_id: int | None = None,
        catalog_modules_view: CatalogModules = Depends(),
        catalog_requirements_view: CatalogRequirements = Depends(),
        columns: ColumnGroup = Depends(get_catalog_requirement_columns),
        df: DataFrame = Depends(get_uploaded_dataframe),
        skip_blanks: bool = False,  # skip blank cells
        dry_run: bool = False,  # don't save to database
        session: Session = Depends(get_session),
    ) -> list[CatalogRequirement]:
        fallback_catalog_module = (
            catalog_modules_view.get_catalog_module(fallback_catalog_module_id)
            if fallback_catalog_module_id is not None
            else None
        )

        # Import data frame into database
        catalog_requirement_imports = columns.import_from_dataframe(
            df, skip_none=skip_blanks
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

    return upload_catalog_requirements_dataframe


router.post(
    "/excel/catalog-requirements",
    summary="Upload catalog requirements from Excel",
    status_code=201,
    response_model=list[CatalogRequirementOutput],
)(_get_upload_catalog_requirements_dataframe_handler(get_dataframe_from_uploaded_excel))

router.post(
    "/csv/catalog-requirements",
    summary="Upload catalog requirements from CSV",
    status_code=201,
    response_model=list[CatalogRequirementOutput],
)(_get_upload_catalog_requirements_dataframe_handler(get_dataframe_from_uploaded_csv))
