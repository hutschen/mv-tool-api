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
import io
from tempfile import NamedTemporaryFile
from unittest.mock import Mock
import pytest
from mvtool.database import CRUDOperations
from mvtool.views.gs import GSBausteinParser, ImportGSBausteinView
from mvtool.models import Project
from mvtool import errors
from mvtool.views.projects import ProjectsView


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
    assert gs_baustein.requirements is not None


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


def test_upload_gs_baustein(
    crud: CRUDOperations,
    projects_view: ProjectsView,
    create_project: Project,
    word_temp_file: NamedTemporaryFile,
):
    upload_file = Mock()
    upload_file.file = io.FileIO("tests/data/gs_bausteine/_valid.docx", "r")

    sut = ImportGSBausteinView(projects_view, crud)
    sut.upload_gs_baustein(
        create_project.id,
        upload_file,
        word_temp_file,
    )

    assert create_project.requirements is not None
    assert len(create_project.requirements) > 0