# coding: utf-8
#
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

from mvtool.models.measures import Measure


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
    compliance_status,
    create_measure: Measure,  # TODO: use measure fixture from test_data instead
):
    create_measure.compliance_status = compliance_status
    create_measure.jira_issue.status.completed = True
    assert create_measure.completion_status_hint == "completed"


@pytest.mark.parametrize("completion_status", ["open", "in progress", None])
def test_measure_completion_status_hint_jira_issue_incomplete(
    completion_status,
    create_measure: Measure,  # TODO: use measure fixture from test_data instead
):
    create_measure.compliance_status = "C"
    create_measure.completion_status = completion_status
    create_measure.jira_issue.status.completed = False
    assert create_measure.completion_status_hint == completion_status


@pytest.mark.parametrize("compliance_status", ["NC", "N/A"])
def test_measure_completion_status_hint_non_compliant(
    compliance_status,
    create_measure: Measure,  # TODO: use measure fixture from test_data instead
):
    create_measure.compliance_status = compliance_status
    assert create_measure.completion_status_hint is None
