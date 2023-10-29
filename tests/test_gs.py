# coding: utf-8
#
# Copyright (C) 2022 Helmar Hutschenreuter
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

from mvtool.gs_parser import GSBausteinParser
from mvtool.gs_parser_xml import GSKompendiumParser
from mvtool.utils import errors


def get_gs_kompendium_filenames():
    for filename in os.listdir("tests/data/gs_kompendium"):
        if filename.endswith(".xml"):
            yield os.path.join("tests/data/gs_kompendium", filename)


@pytest.mark.parametrize("filename", get_gs_kompendium_filenames())
def test_parse_gs_kompendium(filename):
    GSKompendiumParser.parse(filename)


def get_gs_baustein_filenames():
    for filename in os.listdir("tests/data/gs_bausteine"):
        if filename.endswith(".docx") and filename not in (
            "_invalid.docx",
            "_corrupted.docx",
        ):
            yield os.path.join("tests/data/gs_bausteine", filename)


@pytest.mark.parametrize("filename", get_gs_baustein_filenames())
def test_parse_gs_baustein(filename):
    gs_baustein = GSBausteinParser.parse(filename)
    assert gs_baustein is not None
    assert gs_baustein.title is not None
    assert gs_baustein.catalog_requirements is not None


def test_parse_gs_baustein_invalid():
    with pytest.raises(errors.ValueHttpError) as error_info:
        GSBausteinParser.parse("tests/data/gs_bausteine/_invalid.docx")
    assert error_info.value.status_code == 400
    assert error_info.value.detail.startswith("Could not parse")


def test_parse_gs_baustein_corrupted():
    with pytest.raises(errors.ValueHttpError) as error_info:
        GSBausteinParser.parse("tests/data/gs_bausteine/_corrupted.docx")
    assert error_info.value.status_code == 400
    assert error_info.value.detail == "Word file seems to be corrupted"
