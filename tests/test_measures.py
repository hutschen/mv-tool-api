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
from jira import JIRAError
from fastapi import HTTPException
from mvtool.models import (
    Document,
    JiraIssue,
    JiraIssueInput,
    Measure,
    MeasureInput,
    Project,
    Requirement,
)
from mvtool.views.measures import MeasuresView


def test_list_measure(
    measures_view: MeasuresView,
    create_project: Project,
    create_requirement: Requirement,
    create_document: Document,
    create_measure: Measure,
):
    results = list(measures_view.list_measures())

    assert len(results) == 1
    measure = results[0]
    assert isinstance(measure, Measure)
    assert measure.id == create_measure.id
    assert measure.requirement.id == create_requirement.id
    assert measure.document.id == create_document.id
    assert measure.jira_issue.id == create_measure.jira_issue_id
    assert measure.requirement.project.jira_project.id == create_project.jira_project_id


def test_list_measures_without_jira_issue(
    measures_view: MeasuresView,
    create_measure: Measure,
):
    create_measure.jira_issue_id = None

    results = list(measures_view.list_measures())

    assert len(results) == 1
    measure = results[0]
    assert isinstance(measure, Measure)
    assert measure.id == create_measure.id
    assert measure.jira_issue is None


def test_list_measures_by_project(
    measures_view: MeasuresView,
    create_project: Project,
    create_measure: Measure,
):
    results = list(
        measures_view.list_measures([Requirement.project_id == create_project.id])
    )

    assert len(results) == 1
    measure = results[0]
    assert isinstance(measure, Measure)
    assert measure.id == create_measure.id
    assert measure.requirement.project.id == create_project.id
    assert measure.jira_issue.id == create_measure.jira_issue_id
    assert measure.requirement.project.jira_project.id == create_project.jira_project_id


def test_list_measures_by_requirement(
    measures_view: MeasuresView,
    create_requirement: Requirement,
    create_measure: Measure,
):
    results = list(
        measures_view.list_measures([Measure.requirement_id == create_requirement.id])
    )

    assert len(results) == 1
    measure = results[0]
    assert isinstance(measure, Measure)
    assert measure.id == create_measure.id
    assert measure.requirement.id == create_requirement.id


def test_create_measure(
    measures_view: MeasuresView,
    create_project: Project,
    create_requirement: Requirement,
    create_document: Document,
    measure_input: MeasureInput,
):
    measure = measures_view.create_measure(create_requirement.id, measure_input)

    assert isinstance(measure, Measure)
    assert measure.requirement.id == create_requirement.id
    assert measure.document.id == create_document.id
    assert measure.jira_issue.id == measure_input.jira_issue_id
    assert measure.requirement.project.jira_project.id == create_project.jira_project_id


def test_create_measure_without_jira_issue(
    measures_view: MeasuresView,
    create_requirement: Requirement,
    measure_input: MeasureInput,
):
    measure_input.jira_issue_id = None
    measure = measures_view.create_measure(create_requirement.id, measure_input)

    assert isinstance(measure, Measure)
    assert measure.requirement.id == create_requirement.id
    assert measure.jira_issue is None


def test_create_measure_without_document_id(
    measures_view: MeasuresView,
    create_requirement: Requirement,
    measure_input: MeasureInput,
):
    measure_input.document_id = None
    measure = measures_view.create_measure(create_requirement.id, measure_input)

    assert isinstance(measure, Measure)
    assert measure.requirement.id == create_requirement.id
    assert measure.document is None


def test_create_measure_with_invalid_requirement_id(
    measures_view: MeasuresView, measure_input: MeasureInput
):
    with pytest.raises(HTTPException) as excinfo:
        measures_view.create_measure(-1, measure_input)
    assert excinfo.value.status_code == 404


def test_create_measure_with_invalid_jira_issue_id(
    measures_view: MeasuresView,
    create_requirement: Requirement,
    measure_input: MeasureInput,
):
    measure_input.jira_issue_id = "invalid"
    with pytest.raises(JIRAError) as excinfo:
        measures_view.create_measure(create_requirement.id, measure_input)
    assert excinfo.value.status_code == 404


def test_create_measure_with_invalid_document_id(
    measures_view: MeasuresView,
    create_requirement: Requirement,
    measure_input: MeasureInput,
):
    measure_input.document_id = -1
    with pytest.raises(HTTPException) as excinfo:
        measures_view.create_measure(create_requirement.id, measure_input)
    assert excinfo.value.status_code == 404


def test_get_measure(
    measures_view: MeasuresView,
    create_project: Project,
    create_requirement: Requirement,
    create_document: Document,
    create_measure: Measure,
):
    measure = measures_view.get_measure(create_measure.id)

    assert isinstance(measure, Measure)
    assert measure.id == create_measure.id
    assert measure.requirement.id == create_requirement.id
    assert measure.document.id == create_document.id
    assert measure.jira_issue.id == create_measure.jira_issue_id
    assert measure.requirement.project.jira_project.id == create_project.jira_project_id


def test_get_measure_invalid_id(measures_view: MeasuresView):
    with pytest.raises(HTTPException) as excinfo:
        measures_view.get_measure(-1)
    assert excinfo.value.status_code == 404


def test_update_measure(
    measures_view: MeasuresView,
    create_project: Project,
    create_requirement: Requirement,
    create_document: Document,
    create_measure: Measure,
    measure_input: MeasureInput,
):
    orig_summary = create_measure.summary
    measure_input.summary = orig_summary + " (updated)"
    measure = measures_view.update_measure(create_measure.id, measure_input)

    assert isinstance(measure, Measure)
    assert measure.id == create_measure.id
    assert measure.summary != orig_summary
    assert measure.requirement.id == create_requirement.id
    assert measure.document.id == create_document.id
    assert measure.jira_issue.id == measure_input.jira_issue_id
    assert measure.requirement.project.jira_project.id == create_project.jira_project_id


def test_update_measure_with_invalid_jira_issue_id(
    measures_view: MeasuresView, create_measure: Measure, measure_input: MeasureInput
):
    measure_input.jira_issue_id = "invalid"
    with pytest.raises(JIRAError) as excinfo:
        measures_view.update_measure(create_measure.id, measure_input)
    assert excinfo.value.status_code == 404


def test_update_measure_with_invalid_document_id(
    measures_view: MeasuresView, create_measure: Measure, measure_input: MeasureInput
):
    with pytest.raises(HTTPException) as excinfo:
        measure_input.document_id = -1
        measures_view.update_measure(create_measure.id, measure_input)
    assert excinfo.value.status_code == 404


def test_update_measure_with_invalid_id(
    measures_view: MeasuresView, measure_input: MeasureInput
):
    with pytest.raises(HTTPException) as excinfo:
        measures_view.update_measure(-1, measure_input)
    assert excinfo.value.status_code == 404


def test_delete_measure(measures_view: MeasuresView, create_measure: Measure):
    measures_view.delete_measure(create_measure.id)
    with pytest.raises(HTTPException) as excinfo:
        measures_view.get_measure(create_measure.id)
    assert excinfo.value.status_code == 404


def test_create_and_link_jira_issue(
    measures_view: MeasuresView,
    create_measure: Measure,
    jira_issue_input: JiraIssueInput,
):
    create_measure.jira_issue_id = None
    jira_issue = measures_view.create_and_link_jira_issue(
        create_measure.id, jira_issue_input
    )
    assert create_measure.jira_issue_id == jira_issue.id


def test_create_and_link_jira_issue_jira_issue_already_set(
    measures_view: MeasuresView,
    create_measure: Measure,
    jira_issue_input: JiraIssueInput,
):
    with pytest.raises(HTTPException) as excinfo:
        measures_view.create_and_link_jira_issue(create_measure.id, jira_issue_input)
    assert excinfo.value.status_code == 400


def test_create_and_link_jira_issue_jira_project_not_set(
    measures_view: MeasuresView,
    create_measure: Measure,
    jira_issue_input: JiraIssueInput,
):
    create_measure.requirement.project.jira_project_id = None

    with pytest.raises(HTTPException) as excinfo:
        measures_view.create_and_link_jira_issue(create_measure.id, jira_issue_input)
    assert excinfo.value.status_code == 400


def test_link_jira_issue(
    measures_view: MeasuresView,
    create_measure: Measure,
    measure_input: MeasureInput,
    jira_issue: JiraIssue,
):
    measure_input.jira_issue_id = None
    measure_input_update = MeasureInput.from_orm(
        measure_input, update=dict(jira_issue_id=jira_issue.id)
    )
    measure_output = measures_view.update_measure(
        create_measure.id, measure_input_update
    )
    assert measure_output.jira_issue_id == jira_issue.id


def test_unlink_jira_issue(
    measures_view: MeasuresView,
    create_measure: Measure,
    measure_input: MeasureInput,
):
    measure_input.jira_issue_id = None
    measure = measures_view.update_measure(create_measure.id, measure_input)
    assert measure.jira_issue_id is None


def test_measure_jira_issue_without_getter():
    measure = Measure(summary="test", jira_issue_id="test")
    with pytest.raises(AttributeError):
        measure.jira_issue


def test_measure_jira_issue_with_getter():
    jira_issue_dummy = object()
    measure = Measure(summary="test", jira_issue_id="test")
    measure._get_jira_issue = lambda _: jira_issue_dummy
    assert measure.jira_issue == jira_issue_dummy


@pytest.mark.parametrize("compliance_status", ["C", "PC", None])
def test_measure_completion_status_hint_jira_issue_completed(
    compliance_status, create_measure: Measure
):
    create_measure.compliance_status = compliance_status
    create_measure.jira_issue.status.completed = True
    assert create_measure.completion_status_hint == "completed"


@pytest.mark.parametrize("completion_status", ["open", "in progress", None])
def test_measure_completion_status_hint_jira_issue_incomplete(
    completion_status,
    create_measure: Measure,
):
    create_measure.compliance_status = "C"
    create_measure.completion_status = completion_status
    create_measure.jira_issue.status.completed = False
    assert create_measure.completion_status_hint == completion_status


@pytest.mark.parametrize("compliance_status", ["NC", "N/A"])
def test_measure_completion_status_hint_non_compliant(
    compliance_status, create_measure: Measure
):
    create_measure.compliance_status = compliance_status
    assert create_measure.completion_status_hint is None
