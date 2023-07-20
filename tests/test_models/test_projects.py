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
from mvtool.db.schema import Project, Requirement

from mvtool.db.schema import Measure


def test_project_jira_project_without_getter():
    project = Project(name="test", jira_project_id="test")
    with pytest.raises(NotImplementedError):
        project.jira_project


def test_project_jira_project_with_getter():
    jira_project_dummy = object()
    project = Project(name="test", jira_project_id="test")
    project._get_jira_project = lambda _: jira_project_dummy
    assert project.jira_project is jira_project_dummy


def test_project_completion_progress_no_requirements(create_project: Project):
    assert create_project.completion_progress == None


def test_project_completion_progress_no_measures(
    create_project: Project, create_requirement: Requirement
):
    assert create_project.completion_progress == 0.0


def test_project_completion_progress_nothing_to_complete(
    session: Session, create_project: Project, create_requirement: Requirement
):
    create_requirement.compliance_status = "NC"
    session.flush()

    assert create_requirement.completion_progress == None
    assert create_project.completion_progress == None


def test_project_completion_progress_complete(
    session: Session,
    create_project: Project,
    create_requirement: Requirement,
    create_measure: Measure,
):
    create_requirement.compliance_status = "C"
    create_measure.completion_status = "completed"
    session.flush()

    assert create_requirement.completion_progress == 1.0
    assert create_project.completion_progress == 1.0


def test_project_completion_progress_incomplete(
    session: Session,
    create_project: Project,
    create_requirement: Requirement,
    create_measure: Measure,
):
    create_requirement.compliance_status = "C"
    create_measure.completion_status = "open"
    session.flush()

    assert create_requirement.completion_progress == 0.0
    assert create_project.completion_progress == 0.0


def test_project_verification_progress_no_requirements(create_project: Project):
    assert create_project.verification_progress == None


def test_project_verification_progress_no_measures(
    create_project: Project, create_requirement: Requirement
):
    assert len(create_requirement.measures) == 0
    assert create_project.verification_progress == None


def test_project_verification_progress_nothing_to_verify(
    session: Session, create_project: Project, create_requirement: Requirement
):
    create_requirement.compliance_status = "NC"
    session.flush()

    assert create_requirement.verification_progress == None
    assert create_project.verification_progress == None


def test_project_verification_progress_verified(
    session: Session,
    create_project: Project,
    create_requirement: Requirement,
    create_measure: Measure,
):
    create_requirement.compliance_status = "C"
    create_measure.completion_status = "completed"
    create_measure.verification_status = "verified"
    session.flush()

    assert create_requirement.verification_progress == 1.0
    assert create_project.verification_progress == 1.0


def test_project_verification_progress_unverified(
    session: Session,
    create_project: Project,
    create_requirement: Requirement,
    create_measure: Measure,
):
    create_requirement.compliance_status = "C"
    create_measure.completion_status = "completed"
    create_measure.verification_status = "not verified"
    session.flush()

    assert create_requirement.verification_progress == 0.0
    assert create_project.verification_progress == 0.0
