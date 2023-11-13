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

from mvtool.gsparser.common import GSBaustein, GSParseError
from mvtool.gsparser.gs_baustein import parse_gs_baustein_word_file


def get_gs_baustein_filenames():
    for filename in os.listdir("tests/data/gs_bausteine"):
        if filename.endswith(".docx") and filename not in (
            "_invalid.docx",
            "_corrupted.docx",
        ):
            yield os.path.join("tests/data/gs_bausteine", filename)


def iter_gs_baustein(gs_baustein: GSBaustein):
    for gs_anforderung in gs_baustein.gs_anforderungen:
        yield gs_anforderung
        for text in gs_anforderung.text:
            yield text


@pytest.mark.parametrize("filename", get_gs_baustein_filenames())
def test_parse_gs_baustein(filename):
    gs_baustein = parse_gs_baustein_word_file(filename)
    assert gs_baustein is not None
    tuple(iter_gs_baustein(gs_baustein))  # run the parsing process


def test_parse_gs_baustein_invalid():
    """
    Test the parsing of a valid Word file with invalid GS-Baustein content.
    """
    gs_baustein = parse_gs_baustein_word_file("tests/data/gs_bausteine/_invalid.docx")
    assert gs_baustein is not None

    with pytest.raises(GSParseError):
        tuple(iter_gs_baustein(gs_baustein))  # run the parsing process


def test_parse_gs_baustein_corrupted():
    """
    Test the parsing of a corrupted Word file.
    """
    with pytest.raises(GSParseError, match="Word file seems to be corrupt"):
        parse_gs_baustein_word_file("tests/data/gs_bausteine/_corrupted.docx")
