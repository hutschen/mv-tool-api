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

from tempfile import _TemporaryFileWrapper

from fastapi import Depends

from ..db.schema import Catalog, CatalogModule, CatalogRequirement
from ..gsparser.common import GSBaustein, GSKompendium, GSParseError
from ..gsparser.gs_baustein import parse_gs_baustein_word_file
from ..gsparser.gs_kompendium import parse_gs_kompendium_xml_file
from ..utils.errors import ValueHttpError
from ..utils.temp_file import copy_upload_to_temp_file


def get_gs_baustein_from_uploaded_word_file(
    temp_file: _TemporaryFileWrapper = Depends(copy_upload_to_temp_file),
):
    try:
        yield parse_gs_baustein_word_file(temp_file.name)
    except GSParseError as error:
        raise ValueHttpError(str(error)) from error


def get_gs_kompendium_from_uploaded_xml_file(
    temp_file: _TemporaryFileWrapper = Depends(copy_upload_to_temp_file),
):
    try:
        yield parse_gs_kompendium_xml_file(temp_file.name)
    except GSParseError as error:
        raise ValueHttpError(str(error)) from error


def get_catalog_module_from_gs_baustein(
    gs_baustein: GSBaustein = Depends(get_gs_baustein_from_uploaded_word_file),
    skip_omitted: bool = False,
) -> CatalogModule:
    return CatalogModule(
        reference=gs_baustein.title.reference,
        title=gs_baustein.title.name,
        catalog_requirements=[
            CatalogRequirement(
                reference=gs_anforderung.title.reference,
                summary=gs_anforderung.title.name,
                description="\n\n".join(gs_anforderung.text),
                gs_absicherung=gs_anforderung.title.gs_absicherung,
                gs_verantwortliche=gs_anforderung.title.gs_verantwortliche,
            )
            for gs_anforderung in gs_baustein.gs_anforderungen
            if not (skip_omitted and gs_anforderung.omitted)
        ],
    )


def get_catalog_from_gs_kompendium(
    gs_kompendium: GSKompendium = Depends(get_gs_kompendium_from_uploaded_xml_file),
    skip_omitted: bool = False,
) -> Catalog:
    return Catalog(
        title=gs_kompendium.title,
        catalog_modules=[
            get_catalog_module_from_gs_baustein(gs_baustein, skip_omitted)
            for gs_schicht in gs_kompendium.gs_schichten
            for gs_baustein in gs_schicht.gs_bausteine
        ],
    )
