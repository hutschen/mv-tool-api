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

import pytest
from mvtool.database import CRUDOperations
from mvtool.models import (
    CatalogRequirement,
    Document,
    CatalogModule,
    Measure,
    Project,
    Requirement,
)


def test_delete_requirements_of_project(crud: CRUDOperations):
    project = Project(name="test")
    project.requirements = [Requirement(summary="test")]
    crud.create_in_db(project)
    crud.session.commit()

    crud.delete_from_db(Project, project.id)
    crud.session.commit()

    assert crud.session.query(Project).count() == 0
    assert crud.session.query(Requirement).count() == 0


def test_delete_documents_of_project(crud: CRUDOperations):
    project = Project(name="test")
    project.documents = [Document(title="test")]
    crud.create_in_db(project)
    crud.session.commit()

    crud.delete_from_db(Project, project.id)
    crud.session.commit()

    assert crud.session.query(Project).count() == 0
    assert crud.session.query(Document).count() == 0


def test_delete_measures_of_requirement(crud: CRUDOperations):
    requirement = Requirement(summary="test")
    requirement.measures = [Measure(summary="test")]
    crud.create_in_db(requirement)
    crud.session.commit()

    crud.delete_from_db(Requirement, requirement.id)
    crud.session.commit()

    assert crud.session.query(Requirement).count() == 0
    assert crud.session.query(Measure).count() == 0


def test_keep_document_of_when_delete_measure(crud: CRUDOperations):
    measure = Measure(summary="test")
    measure.document = Document(title="test")
    crud.create_in_db(measure)
    crud.session.commit()

    crud.delete_from_db(Measure, measure.id)
    crud.session.commit()

    assert crud.session.query(Measure).count() == 0
    assert crud.session.query(Document).count() == 1


def test_delete_catalog_requirements_of_catalog_module(crud: CRUDOperations):
    catalog_module = CatalogModule(title="test")
    catalog_module.catalog_requirements = [CatalogRequirement(summary="test")]
    crud.create_in_db(catalog_module)
    crud.session.commit()

    crud.delete_from_db(CatalogModule, catalog_module.id)
    crud.session.commit()

    assert crud.session.query(CatalogModule).count() == 0
    assert crud.session.query(CatalogRequirement).count() == 0


@pytest.mark.parametrize("compliance_status", [None, "C", "PC", "NC", "N/A"])
def test_requirement_compliance_status_hint(crud: CRUDOperations, compliance_status):
    requirement = Requirement(summary="test", compliance_status=compliance_status)
    crud.create_in_db(requirement)
    crud.session.commit()

    assert requirement.compliance_status_hint == None


@pytest.mark.parametrize(
    "compliance_states, expected_hint",
    [
        (["C"], "C"),
        (["C", "N/A"], "C"),
        (["C", "NC"], "PC"),
        (["C", "PC"], "PC"),
        (["PC"], "PC"),
        (["NC"], "NC"),
        (["NC", "N/A"], "NC"),
        (["N/A"], "N/A"),
    ],
)
def test_requirement_compliance_status_hint_with_measures(
    crud: CRUDOperations, compliance_states, expected_hint
):
    requirement = Requirement(summary="test")
    requirement.measures = [
        Measure(summary="test", compliance_status=c) for c in compliance_states
    ]
    crud.create_in_db(requirement)
    crud.session.commit()

    assert requirement.compliance_status_hint == expected_hint