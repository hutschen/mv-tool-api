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

from typing import Any
from tempfile import NamedTemporaryFile
from fastapi.responses import FileResponse
from fastapi_utils.cbv import cbv
from fastapi import APIRouter, Depends

from mvtool.views.excel.catalogs import (
    convert_catalog_to_row,
    get_catalog_excel_headers,
)

from .common import ExcelHeader, ExcelView
from ..catalog_modules import (
    CatalogModulesView,
    get_catalog_module_filters,
    get_catalog_module_sort,
)
from ...utils import get_temp_file
from ...models import CatalogModule

router = APIRouter()


def get_catalog_module_excel_headers(
    catalog_headers: list[ExcelHeader] = Depends(get_catalog_excel_headers),
) -> list[ExcelHeader]:
    return [
        *catalog_headers,
        ExcelHeader("Catalog Module ID", optional=True),
        ExcelHeader("Catalog Module Reference", optional=True),
        ExcelHeader("Catalog Module Title"),
        ExcelHeader("Catalog Module Description", optional=True),
    ]


def convert_catalog_module_to_row(
    catalog_module: CatalogModule | None,
) -> dict[str, Any]:
    if catalog_module is None:
        return {
            **convert_catalog_to_row(None),
            "Catalog Module ID": None,
            "Catalog Module Reference": None,
            "Catalog Module Title": None,
            "Catalog Module Description": None,
        }
    return {
        **convert_catalog_to_row(catalog_module.catalog),
        "Catalog Module ID": catalog_module.id,
        "Catalog Module Reference": catalog_module.reference,
        "Catalog Module Title": catalog_module.title,
        "Catalog Module Description": catalog_module.description,
    }


@cbv(router)
class CatalogModulesExcelView(ExcelView):
    kwargs = dict(tags=["excel"])

    def __init__(
        self,
        catalog_modules: CatalogModulesView = Depends(),
        headers: list[ExcelHeader] = Depends(get_catalog_module_excel_headers),
    ):
        ExcelView.__init__(self, headers)
        self._catalog_modules = catalog_modules

    def _convert_to_row(self, catalog_module: CatalogModule) -> dict[str, Any]:
        return convert_catalog_module_to_row(catalog_module)

    @router.get("/excel/catalog_modules", response_class=FileResponse, **kwargs)
    def download_catalog_modules_excel(
        self,
        where_clauses=Depends(get_catalog_module_filters),
        order_by_clauses=Depends(get_catalog_module_sort),
        temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
        sheet_name="Catalog_Modules",
        filename="catalog_modules.xlsx",
    ) -> FileResponse:
        return self._process_download(
            self._catalog_modules.list_catalog_modules(
                where_clauses=where_clauses,
                order_by_clauses=order_by_clauses,
            ),
            temp_file,
            sheet_name=sheet_name,
            filename=filename,
        )
