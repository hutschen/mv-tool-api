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

import re
from xml.etree import ElementTree as ET

from .db.schema import Catalog, CatalogModule, CatalogRequirement


class GSKompendiumParser:
    _requirement_title_re_1 = re.compile(
        r"^\s*([A-Z]{3,4}(\.[A-Z0-9]+)+)\s*(.*?)\s*(\[([^\]]*)\])?\s*\((B|S|H)\)\s*$"
    )
    _requirement_title_re_2 = re.compile(
        r"^\s*([A-Z]{3,4}(\.[A-Z0-9]+)+)\s*(.*?)\s*\((B|S|H)\)\s*(\[([^\]]*)\])?\s*$"
    )
    _gs_baustein_title_re = re.compile(r"^\s*([A-Z]+(\.[0-9]+)+)\s*(.*?)\s*$")
    _gs_schicht_title_re = re.compile(r"^\s*([A-Z]{3,4})\s*(.+)$")
    _xml_namespaces = {"docbook": "http://docbook.org/ns/docbook"}

    @classmethod
    def _parse_requirement_text(cls, section: ET.Element):
        text_paragraphs = []
        for paragraph in section.findall("docbook:para", cls._xml_namespaces):
            text_parts = [text for text in paragraph.itertext()]
            text_paragraphs.append("".join(text_parts))
        return " ".join(text_paragraphs)

    @classmethod
    def _find_subsection(cls, section: ET.Element, title: str):
        for subsection in section.findall("docbook:section", cls._xml_namespaces):
            subsection_title = subsection.find("docbook:title", cls._xml_namespaces)
            if subsection_title is not None and subsection_title.text == title:
                return subsection
        return None

    @classmethod
    def _parse_gs_baustein(cls, section: ET.Element):
        requirements_section = cls._find_subsection(section, "Anforderungen")
        if not requirements_section:
            return

        # fmt: off
        b_section = cls._find_subsection(requirements_section, "Basis-Anforderungen")
        s_section = cls._find_subsection(requirements_section, "Standard-Anforderungen")
        h_section = cls._find_subsection(requirements_section, "Anforderungen bei erhöhtem Schutzbedarf")
        # fmt: on

        for subsection in (b_section, s_section, h_section):
            if subsection is None:
                continue

            for ssubsection in subsection.findall(
                "docbook:section", cls._xml_namespaces
            ):
                title = ssubsection.find("docbook:title", cls._xml_namespaces)
                if title is not None and title.text:
                    match = cls._requirement_title_re_1.match(title.text)
                    if match:
                        yield CatalogRequirement(
                            reference=match.group(1),
                            summary=match.group(3),
                            description=cls._parse_requirement_text(ssubsection),
                            gs_absicherung=match.group(6),
                            gs_verantwortliche=match.group(5),
                        )
                    else:
                        match = cls._requirement_title_re_2.match(title.text)
                        if match:
                            yield CatalogRequirement(
                                reference=match.group(1),
                                summary=match.group(3),
                                description=cls._parse_requirement_text(ssubsection),
                                gs_absicherung=match.group(4),
                                gs_verantwortliche=match.group(6),
                            )
                        else:
                            raise ValueError(
                                f"Could not parse requirement title: {title.text}"
                            )

    @classmethod
    def _parse_gs_schicht(cls, chapter: ET.Element):
        for section in chapter.findall("docbook:section", cls._xml_namespaces):
            title = section.find("docbook:title", cls._xml_namespaces)
            if title is not None and title.text:
                match = cls._gs_baustein_title_re.match(title.text)
                if match:
                    yield CatalogModule(
                        reference=match.group(1),
                        title=match.group(3),
                        catalog_requirements=list(cls._parse_gs_baustein(section)),
                    )
                else:
                    raise ValueError(f"Could not parse GS-Baustein title: {title.text}")

    @classmethod
    def _parse_gs_catalog(cls, root: ET.Element):
        # Find all "Schichten" (layers) of the IT-Grundschutz
        for chapter in root.findall("docbook:chapter", cls._xml_namespaces):
            title = chapter.find("docbook:title", cls._xml_namespaces)
            if title is not None and cls._gs_schicht_title_re.match(title.text):
                for catalog_module in cls._parse_gs_schicht(chapter):
                    yield catalog_module

    @classmethod
    def parse(cls, filename):
        try:
            xml_tree = ET.parse(filename)
        except ET.ParseError as e:
            raise ValueError(f"Could not parse XML file: {e}")
        xml_root = xml_tree.getroot()

        # Create a new catalog
        title = xml_root.find(".//docbook:title", cls._xml_namespaces)
        if title is not None and title.text:
            return Catalog(
                title=title.text,
                catalog_modules=list(cls._parse_gs_catalog(xml_root)),
            )
        else:
            raise ValueError("Could not find catalog title")
