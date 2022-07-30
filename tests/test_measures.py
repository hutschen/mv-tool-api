# coding: utf-8
# 
# Copyright 2022 Helmar Hutschenreuter
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation. You may obtain
# a copy of the GNU AGPL V3 at https://www.gnu.org/licenses/.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AGPL V3 for more details.

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse
from mvtool.models import Project, Document, JiraIssueInput, Measure, MeasureInput, MeasureOutput, Requirement
from mvtool.views.measures import MeasuresView


def test_list_measure_outputs(
        measures_view: MeasuresView, create_requirement: Requirement,
        create_document: Document, create_measure: Measure):
    results = list(measures_view._list_measures(create_requirement.id))

    assert len(results) == 1
    measure_output = results[0]
    assert isinstance(measure_output, MeasureOutput)
    assert measure_output.id == create_measure.id
    assert measure_output.requirement.id == create_requirement.id
    assert measure_output.document.id == create_document.id

def test_list_measure_output_with_jira_issue(
        measures_view: MeasuresView, create_requirement: Requirement,
        create_measure_with_jira_issue: Measure, jira_issue_data):
    result = list(measures_view._list_measures(create_requirement.id))

    measure_output = result[0]
    measure_output.id == create_measure_with_jira_issue.id
    measure_output.jira_issue_id == jira_issue_data.id
    measure_output.jira_issue.id == jira_issue_data.id

def test_create_measure_output(
        measures_view: MeasuresView, create_requirement: Requirement,
        create_document: Document, measure_input: MeasureInput):
    measure_output = measures_view._create_measure(
        create_requirement.id, measure_input)

    assert isinstance(measure_output, MeasureOutput)
    assert measure_output.requirement.id == create_requirement.id
    assert measure_output.document.id == create_document.id

def test_create_measure_invalid_document_id(
        measures_view: MeasuresView, create_requirement: Requirement,
        measure_input: MeasureInput):
    
    with pytest.raises(HTTPException) as excinfo:
        measure_input.document_id = 'invalid'
        measures_view._create_measure(create_requirement.id, measure_input)
        assert excinfo.value.status_code == 404

def test_create_measure_invalid_requirement_id(
        measures_view: MeasuresView, measure_input: MeasureInput):
    
    with pytest.raises(HTTPException) as excinfo:
        measures_view._create_measure('invalid', measure_input)
        assert excinfo.value.status_code == 404

def test_get_measure_output(
        measures_view: MeasuresView, create_requirement: Requirement,
        create_document: Document, create_measure: Measure):
    measure_output = measures_view._get_measure(create_measure.id)

    assert isinstance(measure_output, MeasureOutput)
    assert measure_output.id == create_measure.id
    assert measure_output.requirement.id == create_requirement.id
    assert measure_output.document.id == create_document.id

def test_get_measure_output_with_jira_issue(
        measures_view: MeasuresView, create_measure_with_jira_issue: Measure, 
        jira_issue_data):
    measure_output = measures_view._get_measure(
        create_measure_with_jira_issue.id)

    assert measure_output.id == create_measure_with_jira_issue.id
    assert measure_output.jira_issue_id == jira_issue_data.id
    assert measure_output.jira_issue.id == jira_issue_data.id

def test_get_measure_output_invalid_id(
        measures_view: MeasuresView):
    with pytest.raises(HTTPException) as excinfo:
        measures_view._get_measure('invalid')
        assert excinfo.value.status_code == 404

def test_update_measure_output(
        measures_view: MeasuresView, create_requirement: Requirement,
        create_document: Document, jira_issue_data, create_measure: Measure,
        measure_input: MeasureInput):
    orig_summary = create_measure.summary
    measure_input.summary = orig_summary + ' (updated)'
    measure_output = measures_view._update_measure(
        create_measure.id, measure_input)

    assert isinstance(measure_output, MeasureOutput)
    assert measure_output.id == create_measure.id
    assert measure_output.summary != orig_summary
    assert measure_output.requirement.id == create_requirement.id
    assert measure_output.document.id == create_document.id

def test_update_measure_output_with_jira_issue(
        measures_view: MeasuresView, create_measure_with_jira_issue: Measure, 
        jira_issue_data, measure_input: MeasureInput):
    orig_summary = create_measure_with_jira_issue.summary
    measure_input.summary = orig_summary + ' (updated)'
    measure_output = measures_view._update_measure(
        create_measure_with_jira_issue.id, measure_input)

    assert measure_output.id == create_measure_with_jira_issue.id
    assert measure_output.summary != orig_summary
    assert measure_output.jira_issue_id == jira_issue_data.id
    assert measure_output.jira_issue.id == jira_issue_data.id

def test_update_measure_output_invalid_document_id(
        measures_view: MeasuresView, create_measure: Measure,
        measure_input: MeasureInput):
    with pytest.raises(HTTPException) as excinfo:
        measure_input.document_id = -1
        measures_view._update_measure(create_measure.id, measure_input)
        assert excinfo.value.status_code == 404


def test_update_measure_output_invalid_id(
        measures_view: MeasuresView, measure_input: MeasureInput):
    with pytest.raises(HTTPException) as excinfo:
        measures_view._update_measure(-1, measure_input)
        assert excinfo.value.status_code == 404

def test_delete_measure(measures_view: MeasuresView, create_measure: Measure):
    measures_view.delete_measure(create_measure.id)
    with pytest.raises(HTTPException) as excinfo:
        measures_view.get_measure(create_measure.id)
        assert excinfo.value.status_code == 404

def test_create_and_link_jira_issue(
        measures_view: MeasuresView, create_measure: Measure, 
        jira_issue_input: JiraIssueInput):
    jira_issue = measures_view.create_and_link_jira_issue(
        create_measure.id, jira_issue_input)
    assert create_measure.jira_issue_id == jira_issue.id

def test_create_and_link_jira_issue_jira_issue_already_set(
        measures_view: MeasuresView, create_measure_with_jira_issue: Measure, 
        jira_issue_input: JiraIssueInput):
    with pytest.raises(HTTPException) as excinfo:
        measures_view.create_and_link_jira_issue(
            create_measure_with_jira_issue.id, jira_issue_input)
        assert excinfo.value.status_code == 400

def test_create_and_link_jira_issue_jira_project_not_set(
        measures_view: MeasuresView, create_measure: Measure, 
        jira_issue_input: JiraIssueInput):
    create_measure.requirement.project.jira_project_id = None

    with pytest.raises(HTTPException) as excinfo:
        measures_view.create_and_link_jira_issue(
            create_measure.id, jira_issue_input)
        assert excinfo.value.status_code == 400

def test_unlink_jira_issue(
        measures_view: MeasuresView, create_measure_with_jira_issue: Measure):
    measures_view.unlink_jira_issue(create_measure_with_jira_issue.id)
    assert create_measure_with_jira_issue.jira_issue_id is None

def test_unlink_jira_issue_jira_issue_not_linked(
        measures_view: MeasuresView, create_measure: Measure):
    create_measure.jira_issue_id = None
    with pytest.raises(HTTPException) as excinfo:
        measures_view.unlink_jira_issue(create_measure.id)
        assert excinfo.value.status_code == 404