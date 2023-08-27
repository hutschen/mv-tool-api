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
from sqlalchemy.orm import Session

from mvtool.db.schema import Document, Measure, Project, Requirement
from mvtool.models.common import AutoNumber
from mvtool.models.documents import DocumentPatchMany


@pytest.mark.parametrize(
    "compliance_statuses, expected_count",
    [
        (["C", "PC", None], 3),  # all measures compliant
        (["NC", "N/A"], 0),  # all measures non-compliant
        (["C", "NC"], 1),  # one measure compliant, one measure non-compliant
    ],
)
def test_completion_count(
    session: Session, compliance_statuses: list[str | None], expected_count: int
):
    document = Document(title="test", project=Project(name="test"))
    measures = []

    for compliance_status in compliance_statuses:
        measure = Measure(
            summary="test",
            document=document,
            requirement=Requirement(summary="test", project=document.project),
            compliance_status=compliance_status,
        )
        measures.append(measure)

    session.add_all(measures)
    session.flush()

    assert document.completion_count == expected_count


@pytest.mark.parametrize(
    "completion_statuses, expected_count",
    [
        (["completed", "completed"], 2),  # all measures completed
        (["open", "in progress"], 0),  # all measures incomplete
        (["completed", "open"], 1),  # one measure completed, one measure incomplete
    ],
)
def test_completed_count(
    session: Session, completion_statuses: list[str], expected_count: int
):
    document = Document(title="test", project=Project(name="test"))
    measures = []

    for completion_status in completion_statuses:
        measure = Measure(
            summary="test",
            document=document,
            requirement=Requirement(summary="test", project=document.project),
            completion_status=completion_status,
        )
        measures.append(measure)

    session.add_all(measures)
    session.flush()

    assert document.completed_count == expected_count


@pytest.mark.parametrize(
    "compliance_statuses, verification_methods, expected_count",
    [
        ([None, None, None], ["R", "I", "T"], 3),  # all measures to be verified
        (["C", "NC", "N/A"], [None, "R", "R"], 0),  # no measures to be verified
        ([None, None], [None, "R"], 1),  # one measure to be verified
    ],
)
def test_verification_count(
    session: Session,
    compliance_statuses: str | None,
    verification_methods: str | None,
    expected_count: int,
):
    document = Document(title="test", project=Project(name="test"))
    measures = []

    for compliance_status, verification_method in zip(
        compliance_statuses, verification_methods
    ):
        measure = Measure(
            summary="test",
            document=document,
            requirement=Requirement(summary="test", project=document.project),
            compliance_status=compliance_status,
            verification_method=verification_method,
        )
        measures.append(measure)

    session.add_all(measures)
    session.flush()

    assert document.verification_count == expected_count


@pytest.mark.parametrize(
    "verification_statuses, expected_count",
    [
        (["verified", "verified"], 2),  # all measures verified
        (["partially verified", "not verified"], 0),  # all measures unverified
        (["verified", "not verified"], 1),  # one measure verified and one not
    ],
)
def test_verified_count(
    session: Session, verification_statuses: list[str], expected_count: int
):
    document = Document(title="test", project=Project(name="test"))
    measures = []

    for verification_status in verification_statuses:
        measure = Measure(
            summary="test",
            document=document,
            requirement=Requirement(summary="test", project=document.project),
            completion_status="completed",
            verification_method="R",
            verification_status=verification_status,
        )
        measures.append(measure)

    session.add_all(measures)
    session.flush()

    assert document.verified_count == expected_count


@pytest.mark.parametrize(
    "document_patch_many, expected",
    [
        (
            DocumentPatchMany(title="Test"),
            {"title": "Test"},
        ),
        (
            DocumentPatchMany(reference="Ref", title="Test", description="Desc"),
            {"reference": "Ref", "title": "Test", "description": "Desc"},
        ),
        (
            DocumentPatchMany(reference=AutoNumber(kind="number"), title="Test"),
            {"reference": AutoNumber(kind="number").to_value(0), "title": "Test"},
        ),
    ],
)
def test_document_patch_many_to_patch(
    document_patch_many: DocumentPatchMany, expected: dict
):
    patch = document_patch_many.to_patch(0)
    assert patch.model_dump(exclude_unset=True) == expected
