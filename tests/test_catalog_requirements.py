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

from fastapi import HTTPException
import pytest
from mvtool.models import CatalogModule, CatalogRequirement, CatalogRequirementInput
from mvtool.views.catalog_requirements import CatalogRequirementsView


def test_list_catalog_requirements(
    catalog_requirements_view: CatalogRequirementsView,
    create_catalog_requirement: CatalogRequirement,
):
    results = catalog_requirements_view.list_catalog_requirements()

    assert len(results) == 1
    catalog_requirement = results[0]
    assert isinstance(catalog_requirement, CatalogRequirement)
    assert catalog_requirement.id == create_catalog_requirement.id


def test_list_catalog_requirements_with_invalid_catalog_module_id(
    catalog_requirements_view: CatalogRequirementsView,
):
    results = catalog_requirements_view.list_catalog_requirements(
        [CatalogRequirement.id == -1]
    )
    assert len(results) == 0


def test_create_catalog_requirement(
    catalog_requirements_view: CatalogRequirementsView,
    create_catalog_module: CatalogModule,
    catalog_requirement_input: CatalogRequirementInput,
):
    catalog_requirement = catalog_requirements_view.create_catalog_requirement(
        create_catalog_module, catalog_requirement_input
    )

    assert isinstance(catalog_requirement, CatalogRequirement)
    assert catalog_requirement.summary == catalog_requirement_input.summary
    assert catalog_requirement.catalog_module.id == create_catalog_module.id


def test_get_catalog_requirement(
    catalog_requirements_view: CatalogRequirementsView,
    create_catalog_module: CatalogModule,
    create_catalog_requirement: CatalogRequirement,
):
    catalog_requirement = catalog_requirements_view.get_catalog_requirement(
        create_catalog_requirement.id
    )

    assert isinstance(catalog_requirement, CatalogRequirement)
    assert catalog_requirement.id == create_catalog_requirement.id
    assert catalog_requirement.catalog_module.id == create_catalog_module.id


def test_get_catalog_requirement_with_invalid_catalog_requirement_id(
    catalog_requirements_view: CatalogRequirementsView,
):
    with pytest.raises(HTTPException):
        catalog_requirements_view.get_catalog_requirement(-1)


def test_update_catalog_requirement(
    catalog_requirements_view: CatalogRequirementsView,
    create_catalog_requirement: CatalogRequirement,
    catalog_requirement_input: CatalogRequirementInput,
):
    orig_summary = catalog_requirement_input.summary
    catalog_requirement_input.summary += " updated"

    catalog_requirements_view.update_catalog_requirement(
        create_catalog_requirement, catalog_requirement_input
    )

    assert isinstance(create_catalog_requirement, CatalogRequirement)

    assert create_catalog_requirement.summary != orig_summary
    assert create_catalog_requirement.summary == catalog_requirement_input.summary


def test_delete_catalog_requirement(
    catalog_requirements_view: CatalogRequirementsView,
    create_catalog_requirement: CatalogRequirement,
):
    catalog_requirements_view.delete_catalog_requirement(create_catalog_requirement)
    with pytest.raises(HTTPException):
        catalog_requirements_view.get_catalog_requirement(create_catalog_requirement.id)
