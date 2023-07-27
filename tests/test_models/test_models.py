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
from sqlalchemy.orm import Session

from mvtool.db.database import create_in_db, delete_from_db
from mvtool.db.schema import (
    CatalogModule,
    CatalogRequirement,
    Document,
    Project,
    Requirement,
)
from mvtool.db.schema import (
    Measure,
)


def test_delete_requirements_of_project(session: Session):
    project = Project(name="test")
    project.requirements = [Requirement(summary="test")]
    project = create_in_db(session, project)
    session.commit()

    delete_from_db(session, project)
    session.commit()

    assert session.query(Project).count() == 0
    assert session.query(Requirement).count() == 0


def test_delete_documents_of_project(session: Session):
    project = Project(name="test")
    project.documents = [Document(title="test")]
    project = create_in_db(session, project)
    session.commit()

    delete_from_db(session, project)
    session.commit()

    assert session.query(Project).count() == 0
    assert session.query(Document).count() == 0


def test_delete_measures_of_requirement(session: Session):
    requirement = Requirement(summary="test")
    requirement.measures = [Measure(summary="test")]
    requirement = create_in_db(session, requirement)
    session.commit()

    delete_from_db(session, requirement)
    session.commit()

    assert session.query(Requirement).count() == 0
    assert session.query(Measure).count() == 0


def test_keep_document_of_when_delete_measure(session: Session):
    measure = Measure(summary="test")
    measure.document = Document(title="test")
    measure = create_in_db(session, measure)
    session.commit()

    delete_from_db(session, measure)
    session.commit()

    assert session.query(Measure).count() == 0
    assert session.query(Document).count() == 1


def test_delete_catalog_requirements_of_catalog_module(session: Session):
    catalog_module = CatalogModule(title="test")
    catalog_module.catalog_requirements = [CatalogRequirement(summary="test")]
    catalog_module = create_in_db(session, catalog_module)
    session.commit()

    delete_from_db(session, catalog_module)
    session.commit()

    assert session.query(CatalogModule).count() == 0
    assert session.query(CatalogRequirement).count() == 0


@pytest.mark.parametrize(
    "compliance_states, expected_hint",
    [
        ([], None),
        ([None], None),
        (["C"], "C"),
        (["C", "N/A"], "C"),
        (["C", "NC"], "PC"),
        (["C", "PC"], "PC"),
        (["PC"], "PC"),
        (["PC", "N/A"], "PC"),
        (["NC"], "NC"),
        (["NC", "N/A"], "NC"),
        (["N/A"], "N/A"),
    ],
)
def test_requirement_compliance_status_hint_expression(
    session: Session,
    compliance_states,
    expected_hint,
):
    # Create test data
    requirement = Requirement(summary="test", project=Project(name="test"))
    requirement.measures = [
        Measure(summary="test", compliance_status=c) for c in compliance_states
    ]
    session.add(requirement)
    session.flush()

    # Test the class part of the hybrid property
    queried_hint = (
        session.query(Requirement.compliance_status_hint)
        .filter(Requirement.id == requirement.id)
        .scalar()
    )
    assert queried_hint == expected_hint

    # Test the instance part of the hybrid property
    assert requirement.compliance_status_hint == expected_hint
