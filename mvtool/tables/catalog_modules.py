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

from mvtool.utils.temp_file import copy_upload_to_temp_file, get_temp_file

from ..models import CatalogModule, CatalogModuleOutput
from ..views.catalog_modules import (
    CatalogModulesView,
    get_catalog_module_filters,
    get_catalog_module_sort,
)
from .catalogs import CatalogImport, get_catalog_columns_def
from .common import ColumnDef, ColumnsDef


class CatalogModuleImport(BaseModel):
    id: int | None = None
    reference: str | None
    title: str
    description: str | None
    catalog: CatalogImport | None = None


def get_catalog_module_columns_def(
    catalog_columns_def: ColumnsDef = Depends(get_catalog_columns_def),
) -> ColumnsDef[CatalogModuleImport, CatalogModule]:
    catalog_columns_def.attr_name = "catalog"

    return ColumnsDef(
        CatalogModuleImport,
        "Catalog Module",
        [
            catalog_columns_def,
            ColumnDef("ID", "id"),
            ColumnDef("Reference", "reference"),
            ColumnDef("Title", "title", required=True),
            ColumnDef("Description", "description"),
        ],
    )


router = APIRouter()


@router.get(
    "/excel/catalog_modules", response_class=FileResponse, **CatalogModulesView.kwargs
)
def download_catalog_modules_excel(
    catalog_modules_view: CatalogModulesView = Depends(),
    where_clauses=Depends(get_catalog_module_filters),
    sort_clauses=Depends(get_catalog_module_sort),
    columns_def: ColumnsDef = Depends(get_catalog_module_columns_def),
    temp_file=Depends(get_temp_file(".xlsx")),
    sheet_name="Catalog Modules",
    filename="catalog_modules.xlsx",
) -> FileResponse:
    catalog_modules = catalog_modules_view.list_catalog_modules(
        where_clauses, sort_clauses
    )
    df = columns_def.export_to_dataframe(catalog_modules)
    df.to_excel(temp_file, sheet_name=sheet_name, index=False)
    return FileResponse(temp_file.name, filename=filename)


@router.post(
    "/excel/catalog_modules",
    status_code=201,
    response_model=list[CatalogModuleOutput],
    **CatalogModulesView.kwargs,
)
def upload_catalog_modules_excel(
    catalog_modules_view: CatalogModulesView = Depends(),
    columns_def: ColumnsDef = Depends(get_catalog_module_columns_def),
    temp_file=Depends(copy_upload_to_temp_file),
    sheet_name="Catalog Modules",
    dry_run: bool = False,  # don't save to database
) -> list[CatalogModuleOutput]:
    df = pd.read_excel(temp_file, sheet_name=sheet_name)
    catalog_module_imports = columns_def.import_from_dataframe(df)
    list(catalog_module_imports)
    # TODO: validate catalog module imports and perform import
    return []
