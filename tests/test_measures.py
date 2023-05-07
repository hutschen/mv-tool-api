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
from fastapi import HTTPException

from mvtool.handlers.jira_ import JiraIssues, JiraProjects
from mvtool.handlers.measures import Measures, create_and_link_jira_issue_to_measure
from mvtool.models import JiraIssue, JiraIssueInput, Measure, MeasureInput


def test_create_and_link_jira_issue(
    measures_view: Measures,
    jira_issues: JiraIssues,
    jira_projects: JiraProjects,
    create_measure: Measure,
    jira_issue_input: JiraIssueInput,
):
    create_measure.jira_issue_id = None
    jira_issue = create_and_link_jira_issue_to_measure(
        create_measure.id,
        jira_issue_input,
        measures_view,
        jira_issues,
        jira_projects,
    )
    assert create_measure.jira_issue_id == jira_issue.id


def test_create_and_link_jira_issue_jira_project_not_set(
    measures_view: Measures,
    jira_issues: JiraIssues,
    jira_projects: JiraProjects,
    create_measure: Measure,
    jira_issue_input: JiraIssueInput,
):
    create_measure.requirement.project.jira_project_id = None

    with pytest.raises(HTTPException) as excinfo:
        create_and_link_jira_issue_to_measure(
            create_measure.id,
            jira_issue_input,
            measures_view,
            jira_issues,
            jira_projects,
        )
    assert excinfo.value.status_code == 400


def test_link_jira_issue(
    measures_view: Measures,
    create_measure: Measure,
    measure_input: MeasureInput,
    jira_issue: JiraIssue,
):
    measure_input.jira_issue_id = None
    create_measure.jira_issue_id = None

    measure_input_update = MeasureInput.from_orm(
        measure_input, update=dict(jira_issue_id=jira_issue.id)
    )

    measures_view.update_measure(create_measure, measure_input_update)
    assert create_measure.jira_issue_id == jira_issue.id


def test_unlink_jira_issue(
    measures_view: Measures,
    create_measure: Measure,
    measure_input: MeasureInput,
):
    measure_input.jira_issue_id = None
    measures_view.update_measure(create_measure, measure_input)
    assert create_measure.jira_issue_id is None
