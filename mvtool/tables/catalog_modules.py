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
from ..db.schema import CatalogModule
from ..handlers.catalog_modules import (
    CatalogModules,
    get_catalog_module_filters,
    get_catalog_module_sort,
)
from ..handlers.catalogs import Catalogs
from ..models import CatalogModuleImport, CatalogModuleOutput
from .catalogs import get_catalog_columns
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


def get_catalog_module_columns(
    catalog_columns: ColumnGroup = Depends(get_catalog_columns),
) -> ColumnGroup[CatalogModuleImport, CatalogModule]:
    catalog_columns.attr_name = "catalog"

    return ColumnGroup(
        CatalogModuleImport,
        "Catalog Module",
        [
            catalog_columns,
            Column("ID", "id"),
            Column("Reference", "reference"),
            Column("Title", "title", required=True),
            Column("Description", "description"),
        ],
    )


router = APIRouter(tags=["catalog-module"])

router.get(
    "/excel/catalog-modules/column-names",
    summary="Get column names for catalog module Excel export",
    response_model=list[str],
)(get_export_labels_handler(get_catalog_module_columns))


def _get_catalog_modules_dataframe(
    catalog_modules: CatalogModules = Depends(),
    where_clauses=Depends(get_catalog_module_filters),
    sort_clauses=Depends(get_catalog_module_sort),
    columns: ColumnGroup = Depends(hide_columns(get_catalog_module_columns)),
) -> DataFrame:
    catalog_module_list = catalog_modules.list_catalog_modules(
        where_clauses, sort_clauses
    )
    return columns.export_to_dataframe(catalog_module_list)


router.get(
    "/excel/catalog-modules",
    summary="Download catalog modules as Excel file",
    response_class=FileResponse,
)(
    get_download_excel_handler(
        _get_catalog_modules_dataframe,
        sheet_name="Catalog Modules",
        filename="catalog_modules.xlsx",
    )
)

router.get(
    "/csv/catalog-modules",
    summary="Download catalog modules as CSV file",
    response_class=FileResponse,
)(
    get_download_csv_handler(
        _get_catalog_modules_dataframe,
        filename="catalog_modules.csv",
    )
)


def _get_upload_catalog_modules_dataframe_handler(
    get_uploaded_dataframe: Callable,
) -> Callable:
    def upload_catalog_modules_dataframe(
        fallback_catalog_id: int | None = None,
        catalogs_view: Catalogs = Depends(),
        catalog_modules_view: CatalogModules = Depends(),
        columns: ColumnGroup = Depends(get_catalog_module_columns),
        df: DataFrame = Depends(get_uploaded_dataframe),
        skip_blanks: bool = False,  # skip blank cells
        dry_run: bool = False,  # don't save to database
        session: Session = Depends(get_session),
    ) -> list[CatalogModule]:
        fallback_catalog = (
            catalogs_view.get_catalog(fallback_catalog_id)
            if fallback_catalog_id is not None
            else None
        )

        # Import data frame into database
        catalog_module_imports = columns.import_from_dataframe(
            df, skip_none=skip_blanks
        )
        catalog_modules = list(
            catalog_modules_view.bulk_create_update_catalog_modules(
                catalog_module_imports, fallback_catalog, patch=True, skip_flush=dry_run
            )
        )

        # Rollback if dry run
        if dry_run:
            session.rollback()
            return []
        return catalog_modules

    return upload_catalog_modules_dataframe


router.post(
    "/excel/catalog-modules",
    summary="Upload catalog modules from Excel file",
    status_code=201,
    response_model=list[CatalogModuleOutput],
)(_get_upload_catalog_modules_dataframe_handler(get_dataframe_from_uploaded_excel))

router.post(
    "/csv/catalog-modules",
    summary="Upload catalog modules from CSV file",
    status_code=201,
    response_model=list[CatalogModuleOutput],
)(_get_upload_catalog_modules_dataframe_handler(get_dataframe_from_uploaded_csv))
