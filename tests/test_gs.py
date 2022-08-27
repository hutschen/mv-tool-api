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
from mvtool.views.gs import GSBausteinParser


def get_gs_baustein_filenames():
    for filename in os.listdir("tests/data/gs_bausteine"):
        if filename.endswith(".docx"):
            yield os.path.join("tests/data/gs_bausteine", filename)


@pytest.mark.parametrize("filename", get_gs_baustein_filenames())
def test_parse_gs_baustein(filename):
    gs_baustein = GSBausteinParser.parse(filename)
    assert gs_baustein is not None
    assert gs_baustein.title is not None
    assert gs_baustein.requirements is not None
