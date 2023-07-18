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


@pytest.mark.parametrize(
    "compliance_statuses, expected_count",
    [
        (["C", "PC", None], 3),  # all measures compliant
        (["NC", "N/A"], 0),  # all measures non-compliant
        (["C", "NC"], 1),  # one measure compliant, one measure non-compliant
    ],
)
def test_compliant_count(
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

    assert document.compliant_count == expected_count


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
            verification_status=verification_status,
        )
        measures.append(measure)

    session.add_all(measures)
    session.flush()

    assert document.verified_count == expected_count


def test_document_completion_progress_no_measures(session: Session):
    document = Document(title="test", project=Project(name="test"))
    session.add(document)
    session.flush()

    assert document.completion_progress == None


@pytest.mark.parametrize(
    "compliance_status, expected_progress",
    [(None, 0), ("C", 0), ("PC", 0), ("NC", None), ("N/A", None)],
)
def test_document_completion_progress_by_compliance_status(
    session: Session, compliance_status: str | None, expected_progress: float | None
):
    document = Document(title="test", project=Project(name="test"))
    measure = Measure(
        summary="test",
        document=document,
        requirement=Requirement(summary="test", project=document.project),
        compliance_status=compliance_status,
    )
    session.add(measure)
    session.flush()

    assert document.completion_progress == expected_progress


@pytest.mark.parametrize(
    "completed_measures, incomplete_measures, expected_progress",
    [
        (0, 1, 0.0),  # no measures completed
        (1, 0, 1.0),  # all measures completed
        (1, 1, 1 / 2),  # 50% of measures completed
        (2, 1, 2 / 3),  # more than 50% of measures completed
        (1, 2, 1 / 3),  # less than 50% of measures completed
    ],
)
def test_document_completion_progress(
    session: Session, completed_measures, incomplete_measures, expected_progress
):
    document = Document(title="test", project=Project(name="test"))
    measures = []

    # Add completed measures
    for _ in range(completed_measures):
        measure = Measure(
            summary="test",
            document=document,
            requirement=Requirement(summary="test", project=document.project),
            completion_status="completed",
        )
        measures.append(measure)

    # Add incomplete measures
    for _ in range(incomplete_measures):
        measure = Measure(
            summary="test",
            document=document,
            requirement=Requirement(summary="test", project=document.project),
        )
        measures.append(measure)

    session.add_all(measures)
    session.flush()

    assert document.completion_progress == expected_progress


def test_document_verification_progress_no_measures(session: Session):
    document = Document(title="test", project=Project(name="test"))
    session.add(document)
    session.flush()

    assert document.verification_progress == None


@pytest.mark.parametrize(
    "completion_status, expected_progress",
    [(None, None), ("open", None), ("in progress", None), ("completed", 0)],
)
def test_document_verification_progress_by_completion_status(
    session: Session, completion_status: str, expected_progress: float | None
):
    document = Document(title="test", project=Project(name="test"))
    measure = Measure(
        summary="test",
        document=document,
        requirement=Requirement(summary="test", project=document.project),
        completion_status=completion_status,
    )
    session.add(measure)
    session.flush()

    assert document.verification_progress == expected_progress


@pytest.mark.parametrize(
    "verified_measures, unverified_measures, expected_progress",
    [
        (0, 1, 0.0),  # no measures verified
        (1, 0, 1.0),  # all measures verified
        (1, 1, 1 / 2),  # 50% of measures verified
        (2, 1, 2 / 3),  # more than 50% of measures verified
        (1, 2, 1 / 3),  # less than 50% of measures verified
    ],
)
def test_document_verification_progress(
    session: Session, verified_measures, unverified_measures, expected_progress
):
    document = Document(title="test", project=Project(name="test"))
    measures = []

    # Add verified measures
    for _ in range(verified_measures):
        measure = Measure(
            summary="test",
            document=document,
            requirement=Requirement(summary="test", project=document.project),
            completion_status="completed",
            verification_status="verified",
        )
        measures.append(measure)

    # Add unverified measures
    for _ in range(unverified_measures):
        measure = Measure(
            summary="test",
            document=document,
            requirement=Requirement(summary="test", project=document.project),
            completion_status="completed",
        )
        measures.append(measure)

    session.add_all(measures)
    session.flush()

    assert document.verification_progress == expected_progress
