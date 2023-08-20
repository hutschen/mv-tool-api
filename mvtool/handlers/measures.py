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


from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import constr
from sqlalchemy import Column

from ..data.measures import Measures
from ..db.schema import (
    Catalog,
    CatalogModule,
    CatalogRequirement,
    Document,
    Measure,
    Requirement,
)
from ..handlers.jira_ import JiraIssues, JiraProjects
from ..models.jira_ import JiraIssue, JiraIssueInput
from ..models.measures import (
    MeasureInput,
    MeasureOutput,
    MeasurePatch,
    MeasurePatchMany,
    MeasureRepresentation,
)
from ..utils import combine_flags
from ..utils.errors import ValueHttpError
from ..utils.filtering import (
    filter_by_pattern_many,
    filter_by_values_many,
    filter_for_existence,
    filter_for_existence_many,
    search_columns,
)
from ..utils.pagination import Page, page_params
from .requirements import Requirements


def get_measure_filters(
    # filter by pattern
    reference: str | None = None,
    summary: str | None = None,
    description: str | None = None,
    compliance_comment: str | None = None,
    completion_comment: str | None = None,
    verification_comment: str | None = None,
    target_object: str | None = None,
    milestone: str | None = None,
    neg_reference: bool = False,
    neg_summary: bool = False,
    neg_description: bool = False,
    neg_compliance_comment: bool = False,
    neg_completion_comment: bool = False,
    neg_verification_comment: bool = False,
    neg_target_object: bool = False,
    neg_milestone: bool = False,
    #
    # filter by values
    references: list[str] | None = Query(default=None),
    compliance_statuses: list[str] | None = Query(default=None),
    completion_statuses: list[str] | None = Query(default=None),
    verification_statuses: list[str] | None = Query(default=None),
    verification_methods: list[str] | None = Query(default=None),
    target_objects: list[str] | None = Query(default=None),
    milestones: list[str] | None = Query(default=None),
    neg_references: bool = False,
    neg_compliance_statuses: bool = False,
    neg_completion_statuses: bool = False,
    neg_verification_statuses: bool = False,
    neg_verification_methods: bool = False,
    neg_target_objects: bool = False,
    neg_milestones: bool = False,
    #
    # filter by ids
    ids: list[int] | None = Query(default=None),
    document_ids: list[int] | None = Query(default=None),
    jira_issue_ids: list[str] | None = Query(default=None),
    project_ids: list[int] | None = Query(default=None),
    requirement_ids: list[int] | None = Query(default=None),
    catalog_requirement_ids: list[int] | None = Query(default=None),
    catalog_module_ids: list[int] | None = Query(default=None),
    catalog_ids: list[int] | None = Query(default=None),
    neg_ids: bool = False,
    neg_document_ids: bool = False,
    neg_jira_issue_ids: bool = False,
    neg_project_ids: bool = False,
    neg_requirement_ids: bool = False,
    neg_catalog_requirement_ids: bool = False,
    neg_catalog_module_ids: bool = False,
    neg_catalog_ids: bool = False,
    #
    # filter for existence
    has_reference: bool | None = None,
    has_description: bool | None = None,
    has_compliance_status: bool | None = None,
    has_compliance_comment: bool | None = None,
    has_completion_status: bool | None = None,
    has_completion_comment: bool | None = None,
    has_verification_status: bool | None = None,
    has_verification_method: bool | None = None,
    has_verification_comment: bool | None = None,
    has_document: bool | None = None,
    has_jira_issue: bool | None = None,
    has_catalog: bool | None = None,
    has_catalog_module: bool | None = None,
    has_catalog_requirement: bool | None = None,
    has_target_object: bool | None = None,
    has_milestone: bool | None = None,
    #
    # filter by search string
    search: str | None = None,
) -> list[Any]:
    where_clauses = []

    # filter by pattern
    where_clauses.extend(
        filter_by_pattern_many(
            # fmt: off
            (Measure.reference, reference, neg_reference),
            (Measure.summary, summary, neg_summary),
            (Measure.description, description, neg_description),
            (Measure.compliance_comment, compliance_comment, neg_compliance_comment),
            (Measure.completion_comment, completion_comment, neg_completion_comment),
            (Measure.verification_comment, verification_comment, neg_verification_comment),
            (Requirement.target_object, target_object, neg_target_object),
            (Requirement.milestone, milestone, neg_milestone),
            # fmt: on
        )
    )

    # filter by values or by ids
    where_clauses.extend(
        filter_by_values_many(
            # fmt: off
            (Measure.reference, references, neg_references),
            (Measure.compliance_status, compliance_statuses, neg_compliance_statuses),
            (Measure.completion_status, completion_statuses, neg_completion_statuses),
            (Measure.verification_status, verification_statuses, neg_verification_statuses),
            (Measure.verification_method, verification_methods, neg_verification_methods),
            (Measure.id, ids, neg_ids),
            (Measure.document_id, document_ids, neg_document_ids),
            (Measure.jira_issue_id, jira_issue_ids, neg_jira_issue_ids),
            (Requirement.project_id, project_ids, neg_project_ids),
            (Measure.requirement_id, requirement_ids, neg_requirement_ids),
            (Requirement.catalog_requirement_id, catalog_requirement_ids, neg_catalog_requirement_ids),
            (CatalogRequirement.catalog_module_id, catalog_module_ids, neg_catalog_module_ids),
            (CatalogModule.catalog_id, catalog_ids, neg_catalog_ids),
            (Requirement.target_object, target_objects, neg_target_objects),
            (Requirement.milestone, milestones, neg_milestones),
            # fmt: on
        )
    )

    # filter for existence
    where_clauses.extend(
        filter_for_existence_many(
            (Measure.reference, has_reference),
            (Measure.description, has_description),
            (Measure.compliance_status, has_compliance_status),
            (Measure.compliance_comment, has_compliance_comment),
            (Measure.completion_status, has_completion_status),
            (Measure.completion_comment, has_completion_comment),
            (Measure.verification_status, has_verification_status),
            (Measure.verification_method, has_verification_method),
            (Measure.verification_comment, has_verification_comment),
            (Measure.document_id, has_document),
            (Measure.jira_issue_id, has_jira_issue),
            (
                Requirement.catalog_requirement_id,
                combine_flags(has_catalog_requirement, has_catalog_module, has_catalog),
            ),
            (Requirement.target_object, has_target_object),
            (Requirement.milestone, has_milestone),
        )
    )

    # filter by search string
    if search:
        where_clauses.append(
            search_columns(
                search,
                Measure.reference,
                Measure.summary,
                Measure.description,
                Measure.compliance_comment,
                Measure.completion_comment,
                Measure.verification_comment,
                Document.reference,
                Document.title,
                Requirement.reference,
                Requirement.summary,
                CatalogRequirement.reference,
                CatalogRequirement.summary,
                CatalogModule.reference,
                CatalogModule.title,
                Catalog.reference,
                Catalog.title,
            )
        )

    return where_clauses


def get_measure_sort(
    sort_by: str | None = None,
    sort_order: constr(pattern=r"^(asc|desc)$") | None = None,
) -> list[Any]:
    if not (sort_by and sort_order):
        return []

    try:
        columns: list[Column] = {
            "reference": [Measure.reference],
            "summary": [Measure.summary],
            "description": [Measure.description],
            "compliance_status": [Measure.compliance_status],
            "compliance_comment": [Measure.compliance_comment],
            "completion_status": [Measure.completion_status],
            "completion_comment": [Measure.completion_comment],
            "verification_status": [Measure.verification_status],
            "verification_method": [Measure.verification_method],
            "verification_comment": [Measure.verification_comment],
            "document": [Document.reference, Document.title],
            "jira_issue": [Measure.jira_issue_id],
            "requirement": [Requirement.reference, Requirement.summary],
            "catalog_requirement": [
                CatalogRequirement.reference,
                CatalogRequirement.summary,
            ],
            "catalog_module": [CatalogModule.reference, CatalogModule.title],
            "catalog": [Catalog.reference, Catalog.title],
            "target_object": [Requirement.target_object],
            "milestone": [Requirement.milestone],
        }[sort_by]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by parameter: {sort_by}",
        )

    columns.append(Measure.id)
    if sort_order == "asc":
        return [column.asc() for column in columns]
    else:
        return [column.desc() for column in columns]


router = APIRouter(tags=["measure"])


@router.get("/measures", response_model=Page[MeasureOutput] | list[MeasureOutput])
def get_measures(
    where_clauses=Depends(get_measure_filters),
    order_by_clauses=Depends(get_measure_sort),
    page_params=Depends(page_params),
    measures: Measures = Depends(),
):
    measures_list = measures.list_measures(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        return Page[MeasureOutput](
            items=measures_list,
            total_count=measures.count_measures(where_clauses),
        )
    else:
        return measures_list


@router.post(
    "/requirements/{requirement_id}/measures",
    status_code=201,
    response_model=MeasureOutput,
)
def create_measure(
    requirement_id: int,
    measure_input: MeasureInput,
    requirements: Requirements = Depends(),
    measures: Measures = Depends(),
) -> Measure:
    return measures.create_measure(
        requirements.get_requirement(requirement_id),
        measure_input,
    )


@router.get("/measures/{measure_id}", response_model=MeasureOutput)
def get_measure(measure_id: int, measures: Measures = Depends()) -> Measure:
    return measures.get_measure(measure_id)


@router.put("/measures/{measure_id}", response_model=MeasureOutput)
def update_measure(
    measure_id: int,
    measure_input: MeasureInput,
    measures: Measures = Depends(),
):
    measure = measures.get_measure(measure_id)
    measures.update_measure(measure, measure_input)
    return measure


@router.patch("/measures/{measure_id}", response_model=MeasureOutput)
def patch_measure(
    measure_id: int, measure_patch: MeasurePatch, measures: Measures = Depends()
) -> Measure:
    measure = measures.get_measure(measure_id)
    measures.patch_measure(measure, measure_patch)
    return measure


@router.patch("/measures", response_model=list[MeasureOutput])
def patch_measures(
    measure_patch: MeasurePatchMany,
    where_clauses=Depends(get_measure_filters),
    order_by_clauses=Depends(get_measure_sort),
    measures: Measures = Depends(),
) -> list[Measure]:
    measures_ = measures.list_measures(where_clauses, order_by_clauses)
    for counter, measure in enumerate(measures_):
        measures.patch_measure(
            measure,
            measure_patch.to_patch(counter),
            skip_flush=True,
        )
    measures.session.flush()
    return measures_


@router.delete("/measures/{measure_id}", status_code=204)
def delete_measure(measure_id: int, measures: Measures = Depends()):
    measures.delete_measure(measures.get_measure(measure_id))


@router.delete("/measures", status_code=204)
def delete_measures(
    where_clauses=Depends(get_measure_filters), measures: Measures = Depends()
) -> None:
    measures_ = measures.list_measures(where_clauses)
    for measure in measures_:
        measures.delete_measure(measure, skip_flush=True)
    measures.session.flush()


@router.get(
    "/measure/representations",
    response_model=Page[MeasureRepresentation] | list[MeasureRepresentation],
)
def get_measure_representations(
    where_clauses: list[Any] = Depends(get_measure_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_measure_sort),
    page_params=Depends(page_params),
    measures: Measures = Depends(),
):
    if local_search:
        where_clauses.append(
            search_columns(local_search, Measure.reference, Measure.summary)
        )

    measures_list = measures.list_measures(
        where_clauses, order_by_clauses, **page_params, query_jira=False
    )
    if page_params:
        return Page[MeasureRepresentation](
            items=measures_list,
            total_count=measures.count_measures(where_clauses),
        )
    else:
        return measures_list


@router.get("/measure/field-names", response_model=list[str])
def get_measure_field_names(
    where_clauses=Depends(get_measure_filters),
    measures: Measures = Depends(),
) -> set[str]:
    field_names = {"project", "requirement", "id", "summary", "completion_status"}
    for field, names in [
        (Measure.reference, ["reference"]),
        (Measure.description, ["description"]),
        (Measure.compliance_status, ["compliance_status"]),
        (Measure.compliance_comment, ["compliance_comment"]),
        (Measure.completion_comment, ["completion_comment"]),
        (Measure.verification_status, ["verification_status"]),
        (Measure.verification_method, ["verification_method"]),
        (Measure.verification_comment, ["verification_comment"]),
        (Measure.document_id, ["document"]),
        (Measure.jira_issue_id, ["jira_issue"]),
        (
            Requirement.catalog_requirement_id,
            ["catalog_requirement", "catalog_module", "catalog"],
        ),
        (Requirement.milestone, ["milestone"]),
        (Requirement.target_object, ["target_object"]),
    ]:
        if measures.has_measure([filter_for_existence(field, True), *where_clauses]):
            field_names.update(names)
    return field_names


@router.get("/measure/references", response_model=Page[str] | list[str])
def get_measure_references(
    where_clauses=Depends(get_measure_filters),
    local_search: str | None = None,
    page_params=Depends(page_params),
    measures: Measures = Depends(),
):
    if local_search:
        where_clauses.append(search_columns(local_search, Measure.reference))

    references = measures.list_measure_values(
        Measure.reference, where_clauses, **page_params
    )
    if page_params:
        return Page[str](
            items=references,
            total_count=measures.count_measure_values(Measure.reference, where_clauses),
        )
    else:
        return references


@router.post(
    "/measures/{measure_id}/jira-issue",
    status_code=201,
    response_model=JiraIssue,
    tags=["jira-issue"],
)
def create_and_link_jira_issue_to_measure(
    measure_id: int,
    jira_issue_input: JiraIssueInput,
    measures: Measures = Depends(),
    jira_issues: JiraIssues = Depends(),
    jira_projects: JiraProjects = Depends(),
) -> JiraIssue:
    measure = measures.get_measure(measure_id)

    # check if a Jira project is assigned to corresponding project
    project = measure.requirement.project
    if project.jira_project_id is None:
        raise ValueHttpError(f"No Jira project is assigned to project {project.id}")

    # load jira project to check if user has permission to create Jira issues
    jira_projects.check_jira_project_id(project.jira_project_id)

    # create and link Jira issue
    jira_issue = jira_issues.create_jira_issue(
        project.jira_project_id, jira_issue_input
    )
    measure.jira_issue_id = jira_issue.id
    measures.session.flush()
    return jira_issue
