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
from ..db.schema import Catalog
from ..handlers.catalogs import Catalogs, get_catalog_filters, get_catalog_sort
from ..models import CatalogImport, CatalogOutput
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


def get_catalog_columns() -> ColumnGroup[CatalogImport, Catalog]:
    return ColumnGroup(
        CatalogImport,
        "Catalog",
        [
            Column("ID", "id"),
            Column("Reference", "reference"),
            Column("Title", "title", required=True),
            Column("Description", "description"),
        ],
    )


router = APIRouter(tags=["catalog"])

router.get(
    "/excel/catalogs/column-names",
    summary="Get column names for catalogs Excel export",
    response_model=list[str],
)(get_export_labels_handler(get_catalog_columns))


def _get_catalogs_dataframe(
    catalogs: Catalogs = Depends(),
    where_clauses=Depends(get_catalog_filters),
    sort_clauses=Depends(get_catalog_sort),
    columns: ColumnGroup = Depends(hide_columns(get_catalog_columns)),
) -> DataFrame:
    catalog_list = catalogs.list_catalogs(where_clauses, sort_clauses)
    return columns.export_to_dataframe(catalog_list)


router.get(
    "/excel/catalogs",
    summary="Get catalogs as Excel file",
    response_class=FileResponse,
)(
    get_download_excel_handler(
        _get_catalogs_dataframe,
        sheet_name="Catalogs",
        filename="catalogs.xlsx",
    )
)

router.get(
    "/csv/catalogs", summary="Get catalogs as CSV file", response_class=FileResponse
)(get_download_csv_handler(_get_catalogs_dataframe, filename="catalogs.csv"))


def _get_upload_catalogs_dataframe_handler(
    get_uploaded_dataframe: Callable,
) -> Callable:
    def upload_catalogs_dataframe(
        catalogs_view: Catalogs = Depends(),
        columns: ColumnGroup = Depends(get_catalog_columns),
        df: DataFrame = Depends(get_uploaded_dataframe),
        skip_blanks: bool = False,  # skip blank cells
        dry_run: bool = False,  # don't save to database
        session: Session = Depends(get_session),
    ) -> list[Catalog]:
        # Import data frame into database
        catalog_imports = columns.import_from_dataframe(df, skip_none=skip_blanks)
        catalogs = list(
            catalogs_view.bulk_create_update_catalogs(
                catalog_imports, patch=True, skip_flush=dry_run
            )
        )

        # Rollback if dry run
        if dry_run:
            session.rollback()
            return []
        return catalogs

    return upload_catalogs_dataframe


router.post(
    "/excel/catalogs",
    summary="Upload catalogs from Excel file",
    status_code=201,
    response_model=list[CatalogOutput],
)(_get_upload_catalogs_dataframe_handler(get_dataframe_from_uploaded_excel))

router.post(
    "/csv/catalogs",
    summary="Upload catalogs from CSV file",
    status_code=201,
    response_model=list[CatalogOutput],
)(_get_upload_catalogs_dataframe_handler(get_dataframe_from_uploaded_csv))
