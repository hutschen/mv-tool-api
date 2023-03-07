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
from ..catalogs import get_catalog_filters, get_catalog_sort
from ..catalog_requirements import CatalogRequirementsView
from ...utils import get_temp_file
from ...models import CatalogRequirement

router = APIRouter()


@cbv(router)
class CatalogRequirementsExcelView(ExcelView):
    kwargs = dict(tags=["excel"])

    def __init__(self, catalog_requirements: CatalogRequirementsView = Depends()):
        ExcelView.__init__(
            self,
            [
                ExcelHeader("ID", optional=True),
                ExcelHeader("Reference", optional=True),
                ExcelHeader("Summary"),
                ExcelHeader("Description", optional=True),
                ExcelHeader("GS Absicherung", optional=True),
                ExcelHeader("GS Verantwortliche", optional=True),
            ],
        )
        self._catalog_requirements = catalog_requirements

    def _convert_to_row(
        self, catalog_requirement: CatalogRequirement
    ) -> dict[str, Any]:
        return {
            "ID": catalog_requirement.id,
            "Reference": catalog_requirement.reference,
            "Summary": catalog_requirement.summary,
            "Description": catalog_requirement.description,
            "GS Absicherung": catalog_requirement.gs_absicherung,
            "GS Verantwortliche": catalog_requirement.gs_verantwortliche,
        }

    @router.get("/excel/catalog_requirements", response_class=FileResponse, **kwargs)
    def download_catalog_requirements_excel(
        self,
        where_clauses=Depends(get_catalog_filters),
        order_by_clauses=Depends(get_catalog_sort),
        temp_file: NamedTemporaryFile = Depends(get_temp_file(".xlsx")),
        sheet_name="Catalog_Requirements",
        filename="catalog_requirements.xlsx",
    ) -> FileResponse:
        return self._process_download(
            self._catalog_requirements.list_catalog_requirements(
                where_clauses, order_by_clauses
            ),
            temp_file,
            sheet_name=sheet_name,
            filename=filename,
        )
