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

from pkg_resources import Requirement
from mvtool.database import CRUDOperations
from mvtool.models import Measure, MeasureOutput, RequirementOutput
from mvtool.views.documents import DocumentsView
from mvtool.views.jira_ import JiraIssuesView
from mvtool.views.requirements import RequirementsView
from mvtool.views.measures import MeasuresView


def test_list_measures(crud: CRUDOperations, measure: Measure):
    requirement_id = measure.requirement_id
    crud.read_all_from_db.return_value = [measure]

    sut = MeasuresView(None, None, None, crud)
    results = list(sut.list_measures(requirement_id))

    assert isinstance(results[0], Measure)
    crud.read_all_from_db.assert_called_with(
        Measure, requirement_id=requirement_id)

# def test_list_measures_outputs(
#         jira_issues_view: JiraIssuesView, requirements_view: RequirementsView,
#         documents_view: DocumentsView, crud: CRUDOperations, measure: Measure,
#         requirement: Requirement, requirement_output: RequirementOutput): 
#     requirements_view._get_requirement.return_value = requirement_output
#     crud.read_all_from_db.return_value = [measure]
#     jira_issues_view.get_jira_issues.return_value = []
#     documents_view._get_documents.return_value = None

#     sut = MeasuresView(jira_issues_view, requirements_view, documents_view, crud)
#     results = list(sut._list_measures(measure.id))

#     assert isinstance(results[0], MeasureOutput)
#     requirements_view._get_requirement.assert_called_with(measure.requirement_id)
#     jira_issues_view.get_jira_issues.assert_called_once()
#     documents_view._get_documents.assert_called_with(measure.document_id)
