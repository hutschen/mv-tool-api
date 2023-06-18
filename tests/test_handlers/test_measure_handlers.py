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

import jira
import pytest
from fastapi import HTTPException

from mvtool.data.measures import Measures
from mvtool.data.requirements import Requirements
from mvtool.handlers.measures import (
    create_measure,
    delete_measure,
    get_measure,
    get_measure_field_names,
    get_measure_references,
    get_measure_representations,
    get_measures,
    update_measure,
)
from mvtool.db.schema import CatalogRequirement, Measure, Requirement
from mvtool.db.schema import Document

from mvtool.models.measures import (
    MeasureInput,
    MeasureOutput,
    MeasureRepresentation,
)
from mvtool.db.schema import Project
from mvtool.models.requirements import RequirementInput
from mvtool.utils.pagination import Page


def test_get_measures_list(measures: Measures, measure: Measure):
    measures_list = get_measures([], [], {}, measures)

    assert isinstance(measures_list, list)
    for measure in measures_list:
        assert isinstance(measure, Measure)


def test_get_measures_with_pagination(measures: Measures, measure: Measure):
    page_params = dict(offset=0, limit=1)
    measures_page = get_measures([], [], page_params, measures)

    assert isinstance(measures_page, Page)
    assert measures_page.total_count >= 1
    for measure in measures_page.items:
        assert isinstance(measure, MeasureOutput)


def test_create_measure(
    requirements: Requirements, requirement: Requirement, measures: Measures
):
    measure_input = MeasureInput(summary="New Measure")
    created_measure = create_measure(
        requirement.id, measure_input, requirements, measures
    )

    assert isinstance(created_measure, Measure)
    assert created_measure.summary == measure_input.summary
    assert created_measure.requirement_id == requirement.id


def test_get_measure(measures: Measures, measure: Measure):
    retrieved_measure = get_measure(measure.id, measures)

    assert isinstance(retrieved_measure, Measure)
    assert retrieved_measure.id == measure.id


def test_update_measure(measures: Measures, measure: Measure):
    measure_input = MeasureInput(summary="Updated Measure")
    updated_measure = update_measure(measure.id, measure_input, measures)

    assert isinstance(updated_measure, Measure)
    assert updated_measure.id == measure.id
    assert updated_measure.summary == measure_input.summary


def test_delete_measure(measures: Measures, measure: Measure):
    delete_measure(measure.id, measures)

    with pytest.raises(HTTPException) as excinfo:
        get_measure(measure.id, measures)
    assert excinfo.value.status_code == 404
    assert "No Measure with id" in excinfo.value.detail


def test_get_measure_representations_list(measures: Measures, measure: Measure):
    results = get_measure_representations([], None, [], {}, measures)

    assert isinstance(results, list)
    assert len(results) == 1
    for item in results:
        assert isinstance(item, Measure)


def test_get_measure_representations_with_pagination(
    measures: Measures, measure: Measure
):
    page_params = dict(offset=0, limit=1)
    resulting_page = get_measure_representations([], None, [], page_params, measures)

    assert isinstance(resulting_page, Page)
    assert resulting_page.total_count == 1
    for item in resulting_page.items:
        assert isinstance(item, MeasureRepresentation)


def test_get_measure_representations_local_search(
    requirements: Requirements, requirement: Requirement, measures: Measures
):
    # Create two measures with different summaries
    measure_inputs = [
        MeasureInput(reference="apple", summary="apple_summary"),
        MeasureInput(reference="banana", summary="banana_summary"),
    ]
    for measure_input in measure_inputs:
        create_measure(requirement.id, measure_input, requirements, measures)

    # Get representations with local search
    local_search = "apple"
    results = get_measure_representations([], local_search, [], {}, measures)

    assert isinstance(results, list)
    assert len(results) == 1
    measure = results[0]
    assert isinstance(measure, Measure)
    assert measure.reference == "apple"
    assert measure.summary == "apple_summary"


def test_get_measure_field_names_default_list(measures: Measures):
    field_names = get_measure_field_names([], measures)

    assert isinstance(field_names, set)
    assert field_names == {
        "id",
        "summary",
        "project",
        "requirement",
        "completion_status",
    }


def test_get_measures_field_names_full_list(
    requirements: Requirements,
    project: Project,
    catalog_requirement: CatalogRequirement,
    measures: Measures,
    document: Document,
    jira_issue_data: jira.Issue,
):
    # Create a requirement to get all field names
    requirement_input = RequirementInput(
        reference="reference",
        summary="summary",
        description="description",
        target_object="target_object",
        milestone="milestone",
        catalog_requirement_id=catalog_requirement.id,
    )
    requirement = requirements.create_requirement(project, requirement_input)

    # Create a measure to get all field names
    measure_input = MeasureInput(
        reference="reference",
        summary="summary",
        description="description",
        compliance_status="C",
        compliance_comment="compliance_comment",
        completion_status="completed",
        completion_comment="completion_comment",
        verification_method="R",
        verification_status="verified",
        verification_comment="verification_comment",
        document_id=document.id,
        jira_issue_id=jira_issue_data.id,
    )
    measures.create_measure(requirement, measure_input)

    field_names = get_measure_field_names([], measures)

    # Check if all field names are present
    assert isinstance(field_names, set)
    assert field_names == {
        "id",
        "reference",
        "summary",
        "description",
        "target_object",
        "milestone",
        "compliance_status",
        "compliance_comment",
        "completion_status",
        "completion_comment",
        "verification_method",
        "verification_status",
        "verification_comment",
        "document",
        "jira_issue",
        "project",
        "requirement",
        "catalog_requirement",
        "catalog_module",
        "catalog",
    }


def test_get_measure_references_list(measures: Measures, requirement: Requirement):
    # Create a measure with a reference
    measure_input = MeasureInput(reference="reference", summary="summary")
    measures.create_measure(requirement, measure_input)

    # Get references without pagination
    references = get_measure_references([], None, {}, measures)

    # Check if all references are returned
    assert isinstance(references, list)
    assert references == ["reference"]


def test_get_measure_references_with_pagination(
    measures: Measures, requirement: Requirement
):
    # Create a measure with a reference
    measure_input = MeasureInput(reference="reference", summary="summary")
    measures.create_measure(requirement, measure_input)

    # Get references with pagination
    page_params = dict(offset=0, limit=1)
    references_page = get_measure_references([], None, page_params, measures)

    # Check if all references are returned
    assert isinstance(references_page, Page)
    assert references_page.total_count == 1
    assert references_page.items == ["reference"]


def test_get_measure_references_local_search(
    measures: Measures, requirement: Requirement
):
    # Create two measures with different references
    measure_inputs = [
        MeasureInput(reference="apple", summary="apple_summary"),
        MeasureInput(reference="banana", summary="banana_summary"),
    ]
    for measure_input in measure_inputs:
        measures.create_measure(requirement, measure_input)

    # Get references with local search
    local_search = "apple"
    references = get_measure_references([], local_search, {}, measures)

    # Check if all references are returned
    assert isinstance(references, list)
    assert references == ["apple"]
