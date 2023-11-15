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

import os

import pytest

from mvtool.gsparser.common import GSKompendium, GSParseError
from mvtool.gsparser.gs_kompendium import parse_gs_kompendium_xml_file


def iter_gs_kompendium(gs_kompendium: GSKompendium):
    for gs_schicht in gs_kompendium.gs_schichten:
        yield gs_schicht
        for gs_baustein in gs_schicht.gs_bausteine:
            yield gs_baustein
            for gs_anforderung in gs_baustein.gs_anforderungen:
                yield gs_anforderung
                for text in gs_anforderung.text:
                    yield text


def get_gs_kompendium_filenames():
    for filename in os.listdir("tests/data/gs_kompendium"):
        if filename.endswith(".xml"):
            yield os.path.join("tests/data/gs_kompendium", filename)


@pytest.mark.parametrize("filename", get_gs_kompendium_filenames())
def test_parse_gs_kompendium(filename):
    gs_kompendium = parse_gs_kompendium_xml_file(filename)
    assert gs_kompendium is not None
    tuple(iter_gs_kompendium(gs_kompendium))  # run the parsing process


def test_parse_gs_kompendium_corrupted():
    """
    Test the parsing of a valid XML file with invalid GS-Kompendium content.
    """
    with pytest.raises(GSParseError):
        parse_gs_kompendium_xml_file("tests/data/corrupted")
