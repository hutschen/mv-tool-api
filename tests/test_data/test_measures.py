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

from unittest.mock import Mock

import jira
import pytest
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.sql import select

from mvtool.data.measures import Measures
from mvtool.models.catalog_requirements import CatalogRequirementImport
from mvtool.models.documents import Document, DocumentImport
from mvtool.models.jira_ import JiraIssue, JiraIssueImport
from mvtool.models.measures import Measure, MeasureImport, MeasureInput
from mvtool.models.requirements import Requirement, RequirementImport
from mvtool.utils.errors import NotFoundError, ValueHttpError


def test_modify_measures_query_where_clause(
    session: Session, measures: Measures, requirement: Requirement
):
    # Create some test data
    measure_inputs = [
        MeasureInput(reference="apple", summary="Apple"),
        MeasureInput(reference="banana", summary="Banana"),
        MeasureInput(reference="cherry", summary="Cherry"),
    ]
    for measure_input in measure_inputs:
        measures.create_measure(requirement, measure_input)

    # Test filtering with a single where clause
    where_clauses = [Measure.reference == "banana"]
    query = measures._modify_measures_query(select(Measure), where_clauses)
    results: list[Measure] = session.execute(query).scalars().all()
    assert len(results) == 1
    assert results[0].reference == "banana"


def test_modify_measures_query_order_by(
    session: Session, measures: Measures, requirement: Requirement
):
    # Create some test data
    measure_inputs = [
        MeasureInput(reference="apple", summary="Apple"),
        MeasureInput(reference="banana", summary="Banana"),
        MeasureInput(reference="cherry", summary="Cherry"),
    ]
    for measure_input in measure_inputs:
        measures.create_measure(requirement, measure_input)

    # Test ordering
    order_by_clauses = [desc(Measure.reference)]
    query = measures._modify_measures_query(
        select(Measure), order_by_clauses=order_by_clauses
    )
    results = session.execute(query).scalars().all()
    assert [r.reference for r in results] == ["cherry", "banana", "apple"]


def test_modify_measures_query_offset(
    session: Session, measures: Measures, requirement: Requirement
):
    # Create some test data
    measure_inputs = [
        MeasureInput(reference="apple", summary="Apple"),
        MeasureInput(reference="banana", summary="Banana"),
        MeasureInput(reference="cherry", summary="Cherry"),
    ]
    for measure_input in measure_inputs:
        measures.create_measure(requirement, measure_input)

    # Test offset
    query = measures._modify_measures_query(select(Measure), offset=2)
    results = session.execute(query).scalars().all()
    assert len(results) == 1


def test_modify_measures_query_limit(
    session: Session, measures: Measures, requirement: Requirement
):
    # Create some test data
    measure_inputs = [
        MeasureInput(reference="apple", summary="Apple"),
        MeasureInput(reference="banana", summary="Banana"),
        MeasureInput(reference="cherry", summary="Cherry"),
    ]
    for measure_input in measure_inputs:
        measures.create_measure(requirement, measure_input)

    # Test limit
    query = measures._modify_measures_query(select(Measure), limit=1)
    results = session.execute(query).scalars().all()
    assert len(results) == 1


def test_list_measures(measures: Measures, requirement: Requirement):
    # Create some test data
    measure_inputs = [
        MeasureInput(reference="apple", summary="apple_summary"),
        MeasureInput(reference="banana", summary="banana_summary"),
        MeasureInput(reference="cherry", summary="cherry_summary"),
    ]
    for measure_input in measure_inputs:
        measures.create_measure(requirement, measure_input)

    # Test listing measures without any filters
    results = measures.list_measures(query_jira=False)
    assert len(results) == len(measure_inputs)


def test_list_measures_query_jira(measures: Measures, requirement: Requirement):
    # Create some test data
    measure_input = MeasureInput(reference="reference", summary="summary")
    created_measure = measures.create_measure(requirement, measure_input)

    # Mock _set_jira_issue, _set_jira_project
    measures._set_jira_issue = Mock()
    measures._set_jira_project = Mock()

    # Test listing
    measures.list_measures(query_jira=True)
    measures._set_jira_issue.assert_called_once_with(created_measure, try_to_get=False)
    measures._set_jira_project.assert_called_once_with(created_measure)


def test_count_measures(measures: Measures, requirement: Requirement):
    # Create some test data
    measure_inputs = [
        MeasureInput(reference="apple", summary="apple_summary"),
        MeasureInput(reference="banana", summary="banana_summary"),
        MeasureInput(reference="cherry", summary="cherry_summary"),
    ]
    for measure_input in measure_inputs:
        measures.create_measure(requirement, measure_input)

    # Test counting measures without any filters
    results = measures.count_measures()
    assert results == len(measure_inputs)


def test_list_measure_values(measures: Measures, requirement: Requirement):
    # Create some test data
    measure_inputs = [
        MeasureInput(reference="apple", summary="apple_summary"),
        MeasureInput(reference="apple", summary="banana_summary"),
        MeasureInput(reference="cherry", summary="cherry_summary"),
    ]
    for measure_input in measure_inputs:
        measures.create_measure(requirement, measure_input)

    # Test listing measure values without any filters
    results = measures.list_measure_values(Measure.reference)
    assert len(results) == 2
    assert set(results) == {"apple", "cherry"}


def test_list_measure_values_where_clause(measures: Measures, requirement: Requirement):
    # Create some test data
    measure_inputs = [
        MeasureInput(reference="apple", summary="apple_summary"),
        MeasureInput(reference="apple", summary="banana_summary"),
        MeasureInput(reference="cherry", summary="cherry_summary"),
    ]
    for measure_input in measure_inputs:
        measures.create_measure(requirement, measure_input)

    # Test listing measure values with a where clause
    where_clauses = [Measure.reference == "apple"]
    results = measures.list_measure_values(
        Measure.reference, where_clauses=where_clauses
    )
    assert len(results) == 1
    assert results[0] == "apple"


def test_count_measure_values(measures: Measures, requirement: Requirement):
    # Create some test data
    measure_inputs = [
        MeasureInput(reference="apple", summary="apple_summary"),
        MeasureInput(reference="apple", summary="banana_summary"),
        MeasureInput(reference="cherry", summary="cherry_summary"),
    ]
    for measure_input in measure_inputs:
        measures.create_measure(requirement, measure_input)

    # Test counting measure values without any filters
    results = measures.count_measure_values(Measure.reference)
    assert results == 2


def test_count_measure_values_where_clause(
    measures: Measures, requirement: Requirement
):
    # Create some test data
    measure_inputs = [
        MeasureInput(reference="apple", summary="apple_summary"),
        MeasureInput(reference="apple", summary="banana_summary"),
        MeasureInput(reference="cherry", summary="cherry_summary"),
    ]
    for measure_input in measure_inputs:
        measures.create_measure(requirement, measure_input)

    # Test counting measure values with a where clause
    where_clauses = [Measure.reference == "apple"]
    results = measures.count_measure_values(
        Measure.reference, where_clauses=where_clauses
    )
    assert results == 1


def test_create_measure_from_measure_input(
    measures: Measures,
    requirement: Requirement,
    jira_issue: JiraIssue,
    document: Document,
):
    # Test creating a measure from a measure input
    measure_input = MeasureInput(
        reference="apple",
        summary="apple_summary",
        jira_issue_id=jira_issue.id,
        document_id=document.id,
    )
    measure = measures.create_measure(requirement, measure_input)

    # Check if the measure is created with the correct data
    assert measure.id is not None
    assert measure.reference == measure_input.reference
    assert measure.summary == measure_input.summary
    assert measure.jira_issue_id == measure_input.jira_issue_id
    assert measure.document_id == measure_input.document_id


def test_create_measure_from_measure_import(
    measures: Measures, requirement: Requirement
):
    # Test creating a measure from a measure import with a document import
    measure_import = MeasureImport(
        id=-1,  # should be ignored
        reference="apple",
        summary="apple_summary",
        requirement=RequirementImport(
            reference="banana", summary="banana_summary"
        ),  # should be ignored
        document=DocumentImport(
            reference="cherry", title="cherry_title"
        ),  # should be ignored
    )
    measure = measures.create_measure(requirement, measure_import)

    # Check if the measure is created with the correct data
    assert measure.id is not None
    assert measure.reference == measure_import.reference
    assert measure.summary == measure_import.summary

    # Check if ignored fields are not changed
    assert measure.id != measure_import.id
    assert measure.requirement_id == requirement.id
    assert measure.document_id is None


def test_create_measure_from_measure_input_no_jira_issue_id(
    measures: Measures, requirement: Requirement, document: Document
):
    # Test creating a measure from a measure input
    measure_input = MeasureInput(
        reference="apple", summary="apple_summary", document_id=document.id
    )
    measure = measures.create_measure(requirement, measure_input)

    # Check if the measure is created with the correct data
    assert measure.id is not None
    assert measure.reference == measure_input.reference
    assert measure.summary == measure_input.summary
    assert measure.jira_issue_id is None


def test_create_measure_from_measure_input_invalid_jira_issue_id(
    measures: Measures, requirement: Requirement, document: Document
):
    # Test creating a measure from a measure input
    measure_input = MeasureInput(
        reference="apple",
        summary="apple_summary",
        jira_issue_id=-1,
        document_id=document.id,
    )
    with pytest.raises(jira.JIRAError) as excinfo:
        measures.create_measure(requirement, measure_input)
        assert excinfo.value.status_code == 404


def test_create_measure_from_measure_input_invalid_document_id(
    measures: Measures, requirement: Requirement, jira_issue: JiraIssue
):
    # Test creating a measure from a measure input with an invalid document ID
    measure_input = MeasureInput(
        reference="apple",
        summary="apple_summary",
        jira_issue_id=jira_issue.id,
        document_id=-1,
    )
    with pytest.raises(NotFoundError):
        measures.create_measure(requirement, measure_input)


def test_create_measure_from_measure_input_no_document_id(
    measures: Measures, requirement: Requirement, jira_issue: JiraIssue
):
    # Test creating a measure from a measure input with no document ID
    measure_input = MeasureInput(
        reference="apple", summary="apple_summary", jira_issue_id=jira_issue.id
    )
    measure = measures.create_measure(requirement, measure_input)

    # Check if the measure is created with the correct data
    assert measure.id is not None
    assert measure.reference == measure_input.reference
    assert measure.summary == measure_input.summary
    assert measure.jira_issue_id == measure_input.jira_issue_id
    assert measure.document_id is None


def test_create_measure_skip_flush(
    measures: Measures,
    requirement: Requirement,
    jira_issue: JiraIssue,
    document: Document,
):
    measure_input = MeasureInput(
        reference="apple",
        summary="apple_summary",
        jira_issue_id=jira_issue.id,
        document_id=document.id,
    )
    measures.session = Mock(wraps=measures.session)

    # Test creating a measure without flushing the session
    measures.create_measure(requirement, measure_input, skip_flush=True)

    # Check if the session is not flushed
    measures.session.flush.assert_not_called()


def test_get_measure(
    measures: Measures,
    requirement: Requirement,
    document: Document,
    jira_issue: JiraIssue,
):
    # Create some test data
    measure_input = MeasureInput(
        reference="apple",
        summary="apple_summary",
        document_id=document.id,
        jira_issue_id=jira_issue.id,
    )
    measure = measures.create_measure(requirement, measure_input)

    # Test getting a measure
    result = measures.get_measure(measure.id)

    # Check if the correct measure is returned
    assert result.id == measure.id


def test_get_measure_not_found(measures: Measures):
    # Test getting a measure with an invalid id
    with pytest.raises(NotFoundError):
        measures.get_measure(-1)


def test_update_measure_from_measure_input(
    measures: Measures, requirement: Requirement
):
    # Create a measure using the create_measure method
    measure_input = MeasureInput(summary="summary")
    measure = measures.create_measure(requirement, measure_input)

    # Test updating the measure with MeasureInput
    new_measure_input = MeasureInput(summary="new_summary")
    measures.update_measure(measure, new_measure_input)

    assert measure.summary == new_measure_input.summary


def test_update_measure_with_invalid_document_id(
    measures: Measures, requirement: Requirement
):
    # Create a measure using the create_measure method
    measure_input = MeasureInput(summary="summary")
    measure = measures.create_measure(requirement, measure_input)

    # Update the measure with an invalid document ID
    updated_measure_input = MeasureInput(summary="new_summary", document_id=-1)

    # Test updating a measure with an invalid document ID
    with pytest.raises(NotFoundError):
        measures.update_measure(measure, updated_measure_input)


def test_update_measure_with_invalid_jira_issue_id(
    measures: Measures, requirement: Requirement
):
    # Create a measure using the create_measure method
    measure_input = MeasureInput(summary="summary")
    measure = measures.create_measure(requirement, measure_input)

    # Update the measure with an invalid Jira issue key
    updated_measure_input = MeasureInput(summary="new_summary", jira_issue_id="invalid")

    # Test updating a measure with an invalid Jira issue key
    with pytest.raises(jira.JIRAError) as excinfo:
        measures.update_measure(measure, updated_measure_input)
        assert excinfo.value.status_code == 404


def test_update_measure_from_measure_import(
    measures: Measures,
    requirement: Requirement,
    document: Document,
    jira_issue: JiraIssue,
):
    # Create a measure
    measure_input = MeasureInput(
        reference="apple",
        summary="apple_summary",
        document_id=document.id,
        jira_issue_id=jira_issue.id,
    )
    measure = measures.create_measure(requirement, measure_input)

    # Test updating a measure using MeasureImport
    update_import = MeasureImport(
        id=-1,  # should be ignored
        reference="updated_apple",
        summary="updated_apple_summary",
        requirement=RequirementImport(
            reference="banana", summary="banana_summary"
        ),  # should be ignored
        document=DocumentImport(
            reference="cherry", title="cherry_title"
        ),  # should be ignored
        jira_issue=JiraIssueImport(key="key"),  # should be ignored
    )
    measures.update_measure(measure, update_import)

    # Check if the measure is updated with the correct data
    assert measure.reference == update_import.reference
    assert measure.summary == update_import.summary

    # Check if ignored fields are not changed
    assert measure.id != update_import.id
    assert measure.requirement_id == requirement.id
    assert measure.document_id == document.id
    assert measure.jira_issue_id == jira_issue.id


def test_update_measure_patch_mode(
    measures: Measures,
    requirement: Requirement,
    document: Document,
    jira_issue: JiraIssue,
):
    # Create a measure
    measure_input = MeasureInput(
        reference="apple",
        summary="apple_summary",
        document_id=document.id,
        jira_issue_id=jira_issue.id,
    )
    measure = measures.create_measure(requirement, measure_input)

    # Test updating a measure in patch mode (only specified fields)
    original_reference = measure.reference
    update_input = MeasureInput(summary="updated_apple_summary")
    measures.update_measure(measure, update_input, patch=True)

    # Check if the specified field is updated and other fields remain unchanged
    assert measure.reference == original_reference
    assert measure.summary == update_input.summary


def test_update_measure_skip_flush(
    measures: Measures,
    requirement: Requirement,
    document: Document,
    jira_issue: JiraIssue,
):
    # Create a measure
    measure_input = MeasureInput(
        reference="apple",
        summary="apple_summary",
        document_id=document.id,
        jira_issue_id=jira_issue.id,
    )
    measure = measures.create_measure(requirement, measure_input)

    update_input = MeasureInput(
        reference="updated_apple",
        summary="updated_apple_summary",
        document_id=document.id,
        jira_issue_id=jira_issue.id,
    )
    measures.session = Mock(wraps=measures.session)

    # Test updating a measure without flushing the session
    measures.update_measure(measure, update_input, skip_flush=True)

    # Check if the session is not flushed
    measures.session.flush.assert_not_called()


def test_delete_measure(
    measures: Measures,
    requirement: Requirement,
    document: Document,
    jira_issue: JiraIssue,
):
    # Create some test data
    measure_input = MeasureInput(
        reference="reference",
        summary="summary",
        document_id=document.id,
        jira_issue_id=jira_issue.id,
    )
    measure = measures.create_measure(requirement, measure_input)

    # Test deleting the measure
    measures.delete_measure(measure)

    # Check if the measure is deleted
    with pytest.raises(NotFoundError):
        measures.get_measure(measure.id)


def test_delete_measure_skip_flush(
    measures: Measures,
    requirement: Requirement,
    document: Document,
    jira_issue: JiraIssue,
):
    # Create some test data
    measure_input = MeasureInput(
        reference="reference",
        summary="summary",
        document_id=document.id,
        jira_issue_id=jira_issue.id,
    )
    measure = measures.create_measure(requirement, measure_input)

    measures.session = Mock(wraps=measures.session)

    # Test deleting the measure with skip_flush=True
    measures.delete_measure(measure, skip_flush=True)

    # Check if the flush method was not called
    measures.session.flush.assert_not_called()


def test_bulk_create_update_measures_create(
    measures: Measures, requirement: Requirement
):
    # Create some test data
    measure_imports = [
        MeasureImport(reference="reference1", summary="summary1"),
        MeasureImport(reference="reference2", summary="summary2"),
    ]

    # Test creating measures and provide a fallback requirement
    created_measures = list(
        measures.bulk_create_update_measures(
            measure_imports, fallback_requirement=requirement
        )
    )

    # Check if the measures are created with the correct data
    assert len(created_measures) == 2
    for measure_import, created_measure in zip(measure_imports, created_measures):
        assert created_measure.id is not None
        assert created_measure.summary == measure_import.summary
        assert created_measure.requirement_id == requirement.id


def test_bulk_create_update_measures_create_without_fallback_requirement(
    measures: Measures,
):
    # Create some test data
    measure_imports = [MeasureImport(reference="reference", summary="summary")]

    # Test creating measures without providing a fallback requirement
    with pytest.raises(ValueHttpError):
        list(measures.bulk_create_update_measures(measure_imports))


def test_bulk_create_update_measures_create_with_nested_requirement(
    measures: Measures, requirement: Requirement
):
    # Create some test data
    measure_import = MeasureImport(
        summary="summary",
        requirement=RequirementImport(summary="summary"),
    )

    # Test creating measures with nested requirements
    created_measures = list(
        measures.bulk_create_update_measures(
            [measure_import], fallback_requirement=requirement
        )
    )

    # Check if the measures are created with the correct data
    assert len(created_measures) == 1
    created_measure = created_measures[0]
    assert created_measure.id is not None
    assert created_measure.summary == measure_import.summary
    assert created_measure.requirement_id is not None
    assert created_measure.requirement.summary == measure_import.requirement.summary


def test_bulk_create_update_measures_create_without_fallback_catalog_module(
    measures: Measures, requirement: Requirement
):
    # Create some test data
    measure_import = MeasureImport(
        summary="summary",
        requirement=RequirementImport(
            summary="summary",
            catalog_requirement=CatalogRequirementImport(summary="summary"),
        ),
    )

    # Test creating measures with nested requirements without providing a fallback catalog module
    with pytest.raises(ValueHttpError):
        list(measures.bulk_create_update_measures([measure_import]))


def test_bulk_create_update_measures_create_with_nested_document(
    measures: Measures,
    requirement: Requirement,
):
    # Create some test data
    measure_import = MeasureImport(
        summary="summary", document=DocumentImport(title="title")
    )

    # Test creating measures with nested documents and provide a fallback requirement
    created_measures = list(
        measures.bulk_create_update_measures(
            [measure_import], fallback_requirement=requirement
        )
    )

    # Check if the measures are created with the correct data
    assert len(created_measures) == 1
    created_measure = created_measures[0]
    assert created_measure.id is not None
    assert created_measure.summary == measure_import.summary
    assert created_measure.document_id is not None
    assert created_measure.document.title == measure_import.document.title
    assert created_measure.requirement_id == requirement.id


@pytest.mark.parametrize("patch", [True, False])
def test_bulk_create_update_measures_update(
    measures: Measures, requirement: Requirement, patch: bool
):
    # Create measures to update
    measure_input1 = MeasureInput(summary="summary1")
    measure_input2 = MeasureInput(summary="summary2")
    measure_input3 = MeasureInput(summary="summary3")
    created_measure1 = measures.create_measure(requirement, measure_input1)
    created_measure2 = measures.create_measure(requirement, measure_input2)
    created_measure3 = measures.create_measure(requirement, measure_input3)

    # Create measure imports
    measure_imports = [
        MeasureImport(id=created_measure1.id, summary="new_summary1"),
        MeasureImport(
            id=created_measure2.id,
            summary="new_summary2",
            requirement=RequirementImport(summary="summary"),
        ),
        MeasureImport(
            id=created_measure3.id,
            summary="new_summary3",
            document=DocumentImport(title="title"),
        ),
    ]

    # Update measures using measure imports
    updated_measures = list(
        measures.bulk_create_update_measures(
            measure_imports, fallback_requirement=requirement, patch=patch
        )
    )

    # Check if the measures are updated with the correct data
    assert len(updated_measures) == len(measure_imports)
    for import_, updated in zip(measure_imports, updated_measures):
        assert updated.id == import_.id
        assert updated.summary == import_.summary
        assert updated.requirement_id == requirement.id


def test_bulk_create_update_measures_not_found_error(measures: Measures):
    # Create some test data
    measure_imports = [MeasureImport(id=-1, summary="summary")]

    # Test updating measures with non-existing ids
    with pytest.raises(NotFoundError):
        list(measures.bulk_create_update_measures(measure_imports))


def test_bulk_create_update_measures_with_valid_jira_issue_key(
    measures: Measures, requirement: Requirement, jira_issue: JiraIssue
):
    # Create some test data
    measure_import = MeasureImport(
        summary="summary", jira_issue=JiraIssueImport(key=jira_issue.key)
    )

    # Test creating measures with a valid Jira issue key
    created_measures = list(
        measures.bulk_create_update_measures(
            [measure_import], fallback_requirement=requirement
        )
    )

    # Check if the measures are created with the correct data
    assert len(created_measures) == 1
    assert created_measures[0].jira_issue.key == jira_issue.key


def test_bulk_create_update_measures_with_invalid_jira_issue_key(
    measures: Measures, requirement: Requirement
):
    # Create some test data
    measure_import = MeasureImport(
        summary="summary", jira_issue=JiraIssueImport(key="invalid_key")
    )

    # Test creating measures with an invalid Jira issue key
    with pytest.raises(NotFoundError):
        list(
            measures.bulk_create_update_measures(
                [measure_import], fallback_requirement=requirement
            )
        )


def test_bulk_create_update_measures_skip_flush(
    measures: Measures, requirement: Requirement
):
    measure_imports = [MeasureImport(summary="summary", description="description")]
    measures.session = Mock(wraps=measures.session)

    # Test creating measures with skip_flush=True
    list(
        measures.bulk_create_update_measures(
            measure_imports, fallback_requirement=requirement, skip_flush=True
        )
    )

    # Check if the flush method was not called
    measures.session.flush.assert_not_called()
