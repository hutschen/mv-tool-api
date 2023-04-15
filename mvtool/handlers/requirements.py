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

from typing import Any, Callable, Iterator

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import constr
from sqlmodel import Column, or_

from ..data.requirements import Requirements
from ..models.catalog_modules import CatalogModule
from ..models.catalog_requirements import CatalogRequirement
from ..models.catalogs import Catalog
from ..models.projects import Project
from ..models.requirements import (
    Requirement,
    RequirementInput,
    RequirementOutput,
    RequirementRepresentation,
)
from ..utils import combine_flags
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
    search_columns,
)
from ..utils.pagination import Page, page_params
from .catalog_requirements import CatalogRequirements
from .projects import Projects


def get_requirement_filters(
    # filter by pattern
    reference: str | None = None,
    summary: str | None = None,
    description: str | None = None,
    gs_absicherung: str | None = None,
    gs_verantwortliche: str | None = None,
    target_object: str | None = None,
    milestone: str | None = None,
    compliance_comment: str | None = None,
    #
    # filter by values
    references: list[str] | None = Query(default=None),
    target_objects: list[str] | None = Query(default=None),
    milestones: list[str] | None = Query(default=None),
    compliance_statuses: list[str] | None = Query(default=None),
    #
    # filter by ids
    ids: list[int] | None = Query(default=None),
    project_ids: list[int] | None = Query(default=None),
    catalog_requirement_ids: list[int] | None = Query(default=None),
    catalog_module_ids: list[int] | None = Query(default=None),
    catalog_ids: list[int] | None = Query(default=None),
    #
    # filter for existence
    has_reference: bool | None = None,
    has_description: bool | None = None,
    has_target_object: bool | None = None,
    has_milestone: bool | None = None,
    has_compliance_status: bool | None = None,
    has_compliance_comment: bool | None = None,
    has_catalog: bool | None = None,
    has_catalog_module: bool | None = None,
    has_catalog_requirement: bool | None = None,
    has_gs_absicherung: bool | None = None,
    has_gs_verantwortliche: bool | None = None,
    #
    # filter by search string
    search: str | None = None,
) -> list[Any]:
    where_clauses = []

    # filter by pattern
    for column, value in (
        (Requirement.reference, reference),
        (Requirement.summary, summary),
        (Requirement.description, description),
        (CatalogRequirement.gs_absicherung, gs_absicherung),
        (CatalogRequirement.gs_verantwortliche, gs_verantwortliche),
        (Requirement.target_object, target_object),
        (Requirement.milestone, milestone),
        (Requirement.compliance_comment, compliance_comment),
    ):
        if value:
            where_clauses.append(filter_by_pattern(column, value))

    # filter by values or by ids
    for column, values in (
        (Requirement.reference, references),
        (Requirement.target_object, target_objects),
        (Requirement.milestone, milestones),
        (Requirement.compliance_status, compliance_statuses),
        (Requirement.id, ids),
        (Requirement.project_id, project_ids),
        (Requirement.catalog_requirement_id, catalog_requirement_ids),
        (CatalogRequirement.catalog_module_id, catalog_module_ids),
        (CatalogModule.catalog_id, catalog_ids),
    ):
        if values:
            where_clauses.append(filter_by_values(column, values))

    # filter for existence
    for column, value in (
        (Requirement.reference, has_reference),
        (Requirement.description, has_description),
        (Requirement.target_object, has_target_object),
        (Requirement.milestone, has_milestone),
        (Requirement.compliance_status, has_compliance_status),
        (Requirement.compliance_comment, has_compliance_comment),
        (
            Requirement.catalog_requirement_id,
            combine_flags(has_catalog_requirement, has_catalog_module, has_catalog),
        ),
        (CatalogRequirement.gs_absicherung, has_gs_absicherung),
        (CatalogRequirement.gs_verantwortliche, has_gs_verantwortliche),
    ):
        if value is not None:
            where_clauses.append(filter_for_existence(column, value))

    # filter by search string
    if search:
        where_clauses.append(
            or_(
                filter_by_pattern(column, f"*{search}*")
                for column in (
                    Requirement.reference,
                    Requirement.summary,
                    Requirement.description,
                    Requirement.target_object,
                    Requirement.milestone,
                    Requirement.compliance_comment,
                    CatalogRequirement.reference,
                    CatalogRequirement.summary,
                    CatalogModule.reference,
                    CatalogModule.title,
                    Catalog.reference,
                    Catalog.title,
                )
            )
        )

    return where_clauses


def get_requirement_sort(
    sort_by: str | None = None, sort_order: constr(regex=r"^(asc|desc)$") | None = None
) -> list[Any]:
    if not (sort_by and sort_order):
        return []

    try:
        columns: list[Column] = {
            "reference": [Requirement.reference],
            "summary": [Requirement.summary],
            "description": [Requirement.description],
            "target_object": [Requirement.target_object],
            "milestone": [Requirement.milestone],
            "project": [Project.name],
            "catalog_requirement": [
                CatalogRequirement.reference,
                CatalogRequirement.summary,
            ],
            "catalog_module": [CatalogModule.reference, CatalogModule.title],
            "catalog": [Catalog.reference, Catalog.title],
            "compliance_status": [Requirement.compliance_status],
            "compliance_comment": [Requirement.compliance_comment],
        }[sort_by]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by parameter: {sort_by}",
        )

    columns.append(Requirement.id)
    if sort_order == "asc":
        return [column.asc() for column in columns]
    else:
        return [column.desc() for column in columns]


router = APIRouter(tags=["requirement"])


@router.get(
    "/requirements", response_model=Page[RequirementOutput] | list[RequirementOutput]
)
def get_requirements(
    where_clauses=Depends(get_requirement_filters),
    order_by_clauses=Depends(get_requirement_sort),
    page_params=Depends(page_params),
    requirements: Requirements = Depends(Requirements),
):
    requirements_list = requirements.list_requirements(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        return Page[RequirementOutput](
            items=requirements_list,
            total_count=requirements.count_requirements(where_clauses),
        )
    else:
        return requirements_list


@router.post(
    "/projects/{project_id}/requirements",
    status_code=201,
    response_model=RequirementOutput,
)
def create_requirement(
    project_id: int,
    requirement_input: RequirementInput,
    projects: Projects = Depends(Projects),
    requirements: Requirements = Depends(Requirements),
) -> RequirementOutput:
    return requirements.create_requirement(
        projects.get_project(project_id),
        requirement_input,
    )


@router.get("/requirements/{requirement_id}", response_model=RequirementOutput)
def get_requirement(
    requirement_id: int, requirements: Requirements = Depends(Requirements)
) -> Requirement:
    return requirements.get_requirement(requirement_id)


@router.put("/requirements/{requirement_id}", response_model=RequirementOutput)
def update_requirement(
    requirement_id: int,
    requirement_input: RequirementInput,
    requirements: Requirements = Depends(Requirements),
) -> Requirement:
    requirement = requirements.get_requirement(requirement_id)
    requirements.update_requirement(requirement, requirement_input)
    return requirement


@router.delete("/requirements/{requirement_id}", status_code=204)
def delete_requirement(
    requirement_id: int, requirements: Requirements = Depends(Requirements)
) -> None:
    requirements.delete_requirement(requirements.get_requirement(requirement_id))


@router.post(
    "/projects/{project_id}/requirements/import",
    status_code=201,
    response_model=list[RequirementOutput],
)
def import_requirements_from_catalog_modules(
    project_id: int,
    catalog_module_ids: list[int],
    projects: Projects = Depends(Projects),
    catalog_requirements: CatalogRequirements = Depends(),
    requirements: Requirements = Depends(Requirements),
) -> Iterator[Requirement]:
    return requirements.bulk_create_requirements_from_catalog_requirements(
        projects.get_project(project_id),
        catalog_requirements.list_catalog_requirements(
            [filter_by_values(CatalogRequirement.catalog_module_id, catalog_module_ids)]
        ),
    )


@router.get(
    "/requirement/representations",
    response_model=Page[RequirementRepresentation] | list[RequirementRepresentation],
)
def get_requirement_representations(
    where_clauses: list[Any] = Depends(get_requirement_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_requirement_sort),
    page_params=Depends(page_params),
    requirements: Requirements = Depends(Requirements),
):
    if local_search:
        where_clauses.append(
            search_columns(local_search, Requirement.reference, Requirement.summary)
        )

    requirements_list = requirements.list_requirements(
        where_clauses, order_by_clauses, **page_params, query_jira=False
    )
    if page_params:
        return Page[RequirementRepresentation](
            items=requirements_list,
            total_count=requirements.count_requirements(where_clauses),
        )
    else:
        return requirements_list


@router.get("/requirement/field-names", response_model=list[str])
def get_requirement_field_names(
    where_clauses=Depends(get_requirement_filters),
    requirements: Requirements = Depends(Requirements),
) -> set[str]:
    field_names = {"id", "summary", "project"}
    for field, names in [
        (Requirement.reference, ["reference"]),
        (Requirement.description, ["description"]),
        (Requirement.target_object, ["target_object"]),
        (Requirement.milestone, ["milestone"]),
        (Requirement.compliance_status, ["compliance_status"]),
        (Requirement.compliance_comment, ["compliance_comment"]),
        (
            Requirement.catalog_requirement_id,
            ["catalog_requirement", "catalog_module", "catalog"],
        ),
    ]:
        if requirements.count_requirements(
            [filter_for_existence(field, True), *where_clauses]
        ):
            field_names.update(names)
    return field_names


def _create_requirement_field_values_handler(column: Column) -> Callable:
    def handler(
        where_clauses=Depends(get_requirement_filters),
        local_search: str | None = None,
        page_params=Depends(page_params),
        requirements: Requirements = Depends(Requirements),
    ) -> Page[str] | list[str]:
        if local_search:
            where_clauses.append(search_columns(local_search, column))

        items = requirements.list_requirement_values(
            column, where_clauses, **page_params
        )
        if page_params:
            return Page[str](
                items=items,
                total_count=requirements.count_requirement_values(
                    column, where_clauses
                ),
            )
        else:
            return items

    return handler


router.get(
    "/requirement/references",
    summary="Get requirement references",
    response_model=Page[str] | list[str],
)(_create_requirement_field_values_handler(Requirement.reference))

router.get(
    "/target-objects",
    summary="Get target objects",
    response_model=Page[str] | list[str],
    tags=["target object"],
)(_create_requirement_field_values_handler(Requirement.target_object))

router.get(
    "/milestones",
    summary="Get milestones",
    response_model=Page[str] | list[str],
    tags=["milestone"],
)(_create_requirement_field_values_handler(Requirement.milestone))
