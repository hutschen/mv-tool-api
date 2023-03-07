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

from .common import ExcelHeader, ExcelView
from ..catalogs import CatalogsView, get_catalog_filters, get_catalog_sort
from ...utils import get_temp_file
from ...models import Catalog

router = APIRouter()


@cbv(router)
class CatalogsExcelView(ExcelView):
    kwargs = dict(tags=["excel"])

    def __init__(self, catalogs: CatalogsView = Depends()):
        ExcelView.__init__(
            self,
            [
                ExcelHeader("ID", optional=True),
                ExcelHeader("Reference", optional=True),
                ExcelHeader("Title"),
                ExcelHeader("Description", optional=True),
            ],
        )
        self._catalogs = catalogs

    def _convert_to_row(self, catalog: Catalog) -> dict[str, Any]:
        return {
            "ID": catalog.id,
            "Reference": catalog.reference,
            "Title": catalog.title,
            "Description": catalog.description,
        }

    @router.get("/excel/catalogs", response_class=FileResponse, **kwargs)
    def download_catalogs_excel(
        self,
        where_clauses=Depends(get_catalog_filters),
        order_by_clauses=Depends(get_catalog_sort),
        temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
        sheet_name: str = "Catalogs",
        filename: str = "catalogs.xlsx",
    ) -> FileResponse:
        return self._process_download(
            self._catalogs.list_catalogs(where_clauses, order_by_clauses),
            temp_file,
            sheet_name=sheet_name,
            filename=filename,
        )
