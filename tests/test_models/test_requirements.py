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

from sqlalchemy.orm import Session

from mvtool.models import Measure, Requirement


def test_requirement_completion_progress_incomplete(create_requirement: Requirement):
    assert create_requirement.completion_progress == 0.0


def test_requirement_completion_progress_complete(
    session: Session, create_requirement: Requirement, create_measure: Measure
):
    create_measure.completion_status = "completed"
    session.flush()

    assert create_requirement.completion_progress == 1.0


def test_requirement_completion_progress_ignored(
    session: Session, create_requirement: Requirement
):
    create_requirement.compliance_status = "NC"
    session.flush()

    assert create_requirement.completion_progress == None


def test_requirement_verification_progress_incomplete(create_requirement: Requirement):
    assert create_requirement.verification_progress == 0.0


def test_requirement_verification_progress_complete(
    session: Session, create_requirement: Requirement, create_measure: Measure
):
    create_measure.verification_status = "verified"
    session.flush()

    assert create_requirement.verification_progress == 1.0


def test_requirement_verification_progress_ignored(
    session: Session, create_requirement: Requirement
):
    create_requirement.compliance_status = "NC"
    session.flush()

    assert create_requirement.verification_progress == None
