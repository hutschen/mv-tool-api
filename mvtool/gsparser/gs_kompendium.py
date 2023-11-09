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


from xml.etree import ElementTree as ET

from .common import (
    GS_ANFORDERUNGEN_SECTION_TITLE,
    GS_ANFORDERUNGEN_SUBSECTION_TITLES,
    GSAnforderung,
    GSBaustein,
    GSKompendium,
    GSParseError,
    GSSchicht,
    parse_gs_anforderung_title,
    parse_gs_baustein_title,
    parse_gs_schicht_title,
)

_XML_NAMESPACES = {"docbook": "http://docbook.org/ns/docbook"}


def _find_subsection(section_elem: ET.Element, title: str):
    for subsection_elem in section_elem.findall("docbook:section", _XML_NAMESPACES):
        title_elem = subsection_elem.find("docbook:title", _XML_NAMESPACES)
        if (
            title_elem is not None
            and isinstance(title_elem.text, str)
            and title_elem.text.lower() == title.lower()
        ):
            return subsection_elem


def _parse_gs_anforderung_text(section_elem: ET.Element):
    for paragraph_elem in section_elem.findall("docbook:para", _XML_NAMESPACES):
        yield from paragraph_elem.itertext()


def _parse_gs_anforderungen(section_elem: ET.Element):
    for subsection_elem in section_elem.findall("docbook:section", _XML_NAMESPACES):
        title_elem = subsection_elem.find("docbook:title", _XML_NAMESPACES)
        if title_elem is not None and title_elem.text:
            yield GSAnforderung(
                title=parse_gs_anforderung_title(title_elem.text),
                text=_parse_gs_anforderung_text(subsection_elem),
            )


def _parse_gs_anforderungen_subsections(section_elem: ET.Element):
    for title in GS_ANFORDERUNGEN_SUBSECTION_TITLES:
        subsection_elem = _find_subsection(section_elem, title)
        if subsection_elem is not None:
            yield from _parse_gs_anforderungen(subsection_elem)


def _parse_gs_anforderungen_section(section_elem: ET.Element):
    subsection_elem = _find_subsection(section_elem, GS_ANFORDERUNGEN_SECTION_TITLE)
    if subsection_elem is not None:
        yield from _parse_gs_anforderungen_subsections(subsection_elem)


def _parse_gs_bausteine(chapter_elem: ET.Element):
    for section_elem in chapter_elem.findall("docbook:section", _XML_NAMESPACES):
        title_elem = section_elem.find("docbook:title", _XML_NAMESPACES)
        if title_elem is not None and title_elem.text:
            yield GSBaustein(
                title=parse_gs_baustein_title(title_elem.text),
                gs_anforderungen=_parse_gs_anforderungen_section(section_elem),
            )


def _parse_gs_schichten(root_elem: ET.Element) -> GSKompendium:
    for chapter_elem in root_elem.findall("docbook:chapter", _XML_NAMESPACES):
        title_elem = chapter_elem.find("docbook:title", _XML_NAMESPACES)
        if title_elem is not None and title_elem.text:
            # Not all chapters are GS-Schichten, so the title must be checked
            try:
                title = parse_gs_schicht_title(title_elem.text)
            except GSParseError:
                # Not a GS-Schicht, so it is skipped
                continue

            yield GSSchicht(
                title=title,
                gs_bausteine=_parse_gs_bausteine(chapter_elem),
            )


def parse_gs_kompendium_xml_file(file_name: str) -> GSKompendium:
    try:
        root_elem = ET.parse(file_name).getroot()
    except ET.ParseError as e:
        raise GSParseError(f"XML parsing error: {e}") from e

    return GSKompendium(gs_schichten=_parse_gs_schichten(root_elem))
