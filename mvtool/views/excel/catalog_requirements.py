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

from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from fastapi.responses import FileResponse
from tempfile import NamedTemporaryFile
from typing import Any

from ...models import CatalogRequirement
from ...utils.temp_file import get_temp_file
from ..catalog_requirements import CatalogRequirementsView
from ..catalogs import get_catalog_filters, get_catalog_sort
from .catalog_modules import (
    convert_catalog_module_to_row,
    get_catalog_module_excel_headers,
)
from .common import ExcelHeader, ExcelView

router = APIRouter()


def get_catalog_requirement_excel_headers(
    catalog_module_headers: list[ExcelHeader] = Depends(
        get_catalog_module_excel_headers
    ),
) -> list[ExcelHeader]:
    return [
        *catalog_module_headers,
        ExcelHeader("Catalog Requirement ID", optional=True),
        ExcelHeader("Catalog Requirement Reference", optional=True),
        ExcelHeader("Catalog Requirement Summary"),
        ExcelHeader("Catalog Requirement Description", optional=True),
        ExcelHeader("Catalog Requirement GS Absicherung", optional=True),
        ExcelHeader("Catalog Requirement GS Verantwortliche", optional=True),
    ]


def convert_catalog_requirement_to_row(
    catalog_requirement: CatalogRequirement | None,
) -> dict[str, Any]:
    if not catalog_requirement:
        return {
            **convert_catalog_module_to_row(None),
            "Catalog Requirement ID": None,
            "Catalog Requirement Reference": None,
            "Catalog Requirement Summary": None,
            "Catalog Requirement Description": None,
            "Catalog Requirement GS Absicherung": None,
            "Catalog Requirement GS Verantwortliche": None,
        }
    return {
        **convert_catalog_module_to_row(catalog_requirement.catalog_module),
        "Catalog Requirement ID": catalog_requirement.id,
        "Catalog Requirement Reference": catalog_requirement.reference,
        "Catalog Requirement Summary": catalog_requirement.summary,
        "Catalog Requirement Description": catalog_requirement.description,
        "Catalog Requirement GS Absicherung": catalog_requirement.gs_absicherung,
        "Catalog Requirement GS Verantwortliche": catalog_requirement.gs_verantwortliche,
    }


@cbv(router)
class CatalogRequirementsExcelView(ExcelView):
    kwargs = dict(tags=["excel"])

    def __init__(
        self,
        catalog_requirements: CatalogRequirementsView = Depends(),
        headers: list[ExcelHeader] = Depends(get_catalog_requirement_excel_headers),
    ):
        ExcelView.__init__(self, headers)
        self._catalog_requirements = catalog_requirements

    def _convert_to_row(
        self, catalog_requirement: CatalogRequirement
    ) -> dict[str, Any]:
        return convert_catalog_requirement_to_row(catalog_requirement)

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
