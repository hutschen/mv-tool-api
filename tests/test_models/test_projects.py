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
from mvtool.db.schema import Project


def test_project_jira_project_without_getter():
    project = Project(name="test", jira_project_id="test")
    with pytest.raises(NotImplementedError):
        project.jira_project


def test_project_jira_project_with_getter():
    jira_project_dummy = object()
    project = Project(name="test", jira_project_id="test")
    project._get_jira_project = lambda _: jira_project_dummy
    assert project.jira_project is jira_project_dummy
