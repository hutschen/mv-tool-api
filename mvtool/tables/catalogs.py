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

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlmodel import Session

from ..database import get_session
from ..models import Catalog, CatalogImport, CatalogOutput
from ..utils.temp_file import copy_upload_to_temp_file, get_temp_file
from ..handlers.catalogs import Catalogs, get_catalog_filters, get_catalog_sort
from .common import Column, ColumnGroup
from .handlers import get_export_labels_handler, hide_columns


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


@router.get("/excel/catalogs", response_class=FileResponse)
def download_catalogs_excel(
    catalogs_view: Catalogs = Depends(),
    where_clauses=Depends(get_catalog_filters),
    sort_clauses=Depends(get_catalog_sort),
    columns: ColumnGroup = Depends(hide_columns(get_catalog_columns)),
    temp_file=Depends(get_temp_file(".xlsx")),
    sheet_name="Catalogs",
    filename="catalogs.xlsx",
) -> FileResponse:
    catalogs = catalogs_view.list_catalogs(where_clauses, sort_clauses)
    df = columns.export_to_dataframe(catalogs)
    df.to_excel(temp_file, sheet_name=sheet_name, index=False)
    return FileResponse(temp_file.name, filename=filename)


@router.post("/excel/catalogs", status_code=201, response_model=list[CatalogOutput])
def upload_catalogs_excel(
    catalogs_view: Catalogs = Depends(),
    columns: ColumnGroup = Depends(get_catalog_columns),
    temp_file=Depends(copy_upload_to_temp_file),
    skip_blanks: bool = False,  # skip blank cells
    dry_run: bool = False,  # don't save to database
    session: Session = Depends(get_session),
) -> list[Catalog]:
    # Create data frame from uploaded file
    df = pd.read_excel(temp_file, engine="openpyxl")
    df.drop_duplicates(keep="last", inplace=True)

    # Import data frame into database
    catalog_imports = columns.import_from_dataframe(df, skip_nan=skip_blanks)
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