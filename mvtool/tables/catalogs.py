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
from pydantic import BaseModel

from ..models import Catalog, CatalogOutput
from ..utils.temp_file import copy_upload_to_temp_file, get_temp_file
from ..views.catalogs import CatalogsView, get_catalog_filters, get_catalog_sort
from .common import Column, ColumnsDef


class CatalogImport(BaseModel):
    id: int | None = None
    reference: str | None
    title: str
    description: str | None


def get_catalog_columns_def() -> ColumnsDef[CatalogImport, Catalog]:
    return ColumnsDef(
        CatalogImport,
        "Catalog",
        [
            Column("ID", "id"),
            Column("Reference", "reference"),
            Column("Title", "title", required=True),
            Column("Description", "description"),
        ],
    )


router = APIRouter()


@router.get("/excel/catalogs", response_class=FileResponse, **CatalogsView.kwargs)
def download_catalogs_excel(
    catalogs_view: CatalogsView = Depends(),
    where_clauses=Depends(get_catalog_filters),
    sort_clauses=Depends(get_catalog_sort),
    columns_def: ColumnsDef = Depends(get_catalog_columns_def),
    temp_file=Depends(get_temp_file(".xlsx")),
    sheet_name="Catalogs",
    filename="catalogs.xlsx",
) -> FileResponse:
    catalogs = catalogs_view.list_catalogs(where_clauses, sort_clauses)
    df = columns_def.export_to_dataframe(catalogs)
    df.to_excel(temp_file, sheet_name=sheet_name, index=False)
    return FileResponse(temp_file.name, filename=filename)


@router.post(
    "/excel/catalogs",
    status_code=201,
    response_model=list[CatalogOutput],
    **CatalogsView.kwargs
)
def upload_catalogs_excel(
    catalogs_view: CatalogsView = Depends(),
    columns_def: ColumnsDef = Depends(get_catalog_columns_def),
    temp_file=Depends(copy_upload_to_temp_file),
    dry_run: bool = False,  # don't save to database
) -> list[Catalog]:
    df = pd.read_excel(temp_file, engine="openpyxl")
    catalog_imports = columns_def.import_from_dataframe(df)
    list(catalog_imports)
    # TODO: validate catalog imports and perform import
    return []
