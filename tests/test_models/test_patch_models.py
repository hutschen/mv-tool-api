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

import pytest

from mvtool.models.catalog_modules import CatalogModulePatch
from mvtool.models.catalog_requirements import CatalogRequirementPatch
from mvtool.models.catalogs import CatalogPatch
from mvtool.models.documents import DocumentPatch
from mvtool.models.measures import MeasurePatch
from mvtool.models.projects import ProjectPatch
from mvtool.models.requirements import RequirementPatch


@pytest.mark.parametrize("title_value", [None, ""])
def test_catalog_patch_title_invalid_values(title_value):
    with pytest.raises(ValueError) as excinfo:
        CatalogPatch(title=title_value)
    assert "title must not be empty" in str(excinfo.value)


def test_catalog_patch_title_nonempty_string():
    title = "non-empty string"
    catalog = CatalogPatch(title=title)
    assert catalog.title == title


@pytest.mark.parametrize("title_value", [None, ""])
def test_catalog_module_patch_title_invalid_values(title_value):
    with pytest.raises(ValueError) as excinfo:
        CatalogModulePatch(title=title_value)
    assert "title must not be empty" in str(excinfo.value)


def test_catalog_module_patch_title_nonempty_string():
    title = "non-empty string"
    catalog_module = CatalogModulePatch(title=title)
    assert catalog_module.title == title


@pytest.mark.parametrize("summary_value", [None, ""])
def test_catalog_requirement_patch_summary_invalid_values(summary_value):
    with pytest.raises(ValueError) as excinfo:
        CatalogRequirementPatch(summary=summary_value)
    assert "summary must not be empty" in str(excinfo.value)


def test_catalog_requirement_patch_summary_nonempty_string():
    summary = "non-empty string"
    catalog_requirement = CatalogRequirementPatch(summary=summary)
    assert catalog_requirement.summary == summary


@pytest.mark.parametrize("name_value", [None, ""])
def test_project_patch_name_invalid_values(name_value):
    with pytest.raises(ValueError) as excinfo:
        ProjectPatch(name=name_value)
    assert "name must not be empty" in str(excinfo.value)


def test_project_patch_name_nonempty_string():
    name = "non-empty string"
    project = ProjectPatch(name=name)
    assert project.name == name


@pytest.mark.parametrize("summary_value", [None, ""])
def test_requirement_patch_summary_invalid_values(summary_value):
    with pytest.raises(ValueError) as excinfo:
        RequirementPatch(summary=summary_value)
    assert "summary must not be empty" in str(excinfo.value)


def test_requirement_patch_summary_nonempty_string():
    summary = "non-empty string"
    requirement = RequirementPatch(summary=summary)
    assert requirement.summary == summary


@pytest.mark.parametrize("summary_value", [None, ""])
def test_measure_patch_summary_invalid_values(summary_value):
    with pytest.raises(ValueError) as excinfo:
        MeasurePatch(summary=summary_value)
    assert "summary must not be empty" in str(excinfo.value)


def test_measure_patch_summary_nonempty_string():
    summary = "non-empty string"
    measure = MeasurePatch(summary=summary)
    assert measure.summary == summary


@pytest.mark.parametrize("title_value", [None, ""])
def test_document_patch_title_invalid_values(title_value):
    with pytest.raises(ValueError) as excinfo:
        DocumentPatch(title=title_value)
    assert "title must not be empty" in str(excinfo.value)


def test_document_patch_title_nonempty_string():
    title = "non-empty string"
    document = DocumentPatch(title=title)
    assert document.title == title
