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

from ..db.schema import Project

from ..data.projects import Projects
from ..models.projects import (
    ProjectInput,
    ProjectOutput,
    ProjectRepresentation,
)
from ..utils.filtering import (
    filter_by_pattern_many,
    filter_by_values_many,
    filter_for_existence,
    filter_for_existence_many,
    search_columns,
)
from ..utils.pagination import Page, page_params


def get_project_filters(
    # filter by pattern
    name: str | None = None,
    description: str | None = None,
    neg_name: bool = False,
    neg_description: bool = False,
    #
    # filter by ids
    ids: list[int] | None = Query(None),
    jira_project_ids: list[str] | None = Query(None),
    neg_ids: bool = False,
    neg_jira_project_ids: bool = False,
    #
    # filter for existence
    has_description: bool | None = None,
    has_jira_project: bool | None = None,
    #
    # filter by search string
    search: str | None = None,
) -> list[Any]:
    where_clauses = []

    # filter by pattern
    where_clauses.extend(
        filter_by_pattern_many(
            (Project.name, name, neg_name),
            (Project.description, description, neg_description),
        )
    )

    # filter by ids
    where_clauses.extend(
        filter_by_values_many(
            (Project.id, ids, neg_ids),
            (Project.jira_project_id, jira_project_ids, neg_jira_project_ids),
        )
    )

    # filter for existence
    where_clauses.extend(
        filter_for_existence_many(
            (Project.description, has_description),
            (Project.jira_project_id, has_jira_project),
        )
    )

    # filter by search string
    if search:
        where_clauses.append(search_columns(search, Project.name, Project.description))

    return where_clauses


def get_project_sort(
    sort_by: str | None = None, sort_order: constr(regex=r"^(asc|desc)$") | None = None
) -> list[Any]:
    if not (sort_by and sort_order):
        return []

    try:
        columns: list[Column] = {
            "name": [Project.name],
            "description": [Project.description],
            "jira_project": [Project.jira_project_id],
        }[sort_by]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by parameter: {sort_by}",
        )

    columns.append(Project.id)
    if sort_order == "asc":
        return [column.asc() for column in columns]
    else:
        return [column.desc() for column in columns]


router = APIRouter(tags=["project"])


@router.get("/projects", response_model=Page[ProjectOutput] | list[ProjectOutput])
def get_projects(
    where_clauses=Depends(get_project_filters),
    order_by_clauses=Depends(get_project_sort),
    page_params=Depends(page_params),
    projects: Projects = Depends(),
):
    projects_list = projects.list_projects(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        return Page[ProjectOutput](
            items=projects_list,
            total_count=projects.count_projects(where_clauses),
        )
    else:
        return projects_list


@router.post("/projects", status_code=201, response_model=ProjectOutput)
def create_project(project: ProjectInput, projects: Projects = Depends()) -> Project:
    return projects.create_project(project)


@router.get("/projects/{project_id}", response_model=ProjectOutput)
def get_project(project_id: int, projects: Projects = Depends()) -> Project:
    return projects.get_project(project_id)


@router.put("/projects/{project_id}", response_model=ProjectOutput)
def update_project(
    project_id: int,
    project_input: ProjectInput,
    projects: Projects = Depends(),
) -> Project:
    project = projects.get_project(project_id)
    projects.update_project(project, project_input)
    return project


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int, projects: Projects = Depends()) -> None:
    project = projects.get_project(project_id)
    projects.delete_project(project)


@router.get(
    "/project/representations",
    response_model=Page[ProjectRepresentation] | list[ProjectRepresentation],
)
def get_project_representations(
    where_clauses: list[Any] = Depends(get_project_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_project_sort),
    page_params=Depends(page_params),
    projects: Projects = Depends(),
):
    if local_search:
        where_clauses.append(search_columns(local_search, Project.name))

    projects_list = projects.list_projects(
        where_clauses, order_by_clauses, **page_params, query_jira=False
    )
    if page_params:
        return Page[ProjectRepresentation](
            items=projects_list,
            total_count=projects.count_projects(where_clauses),
        )
    else:
        return projects_list


@router.get("/project/field-names", response_model=list[str])
def get_project_field_names(
    where_clauses=Depends(get_project_filters),
    projects: Projects = Depends(),
) -> set[str]:
    field_names = {"id", "name"}
    for field, names in [
        (Project.description, ["description"]),
        (Project.jira_project_id, ["jira_project"]),
    ]:
        if projects.count_projects([filter_for_existence(field, True), *where_clauses]):
            field_names.update(names)
    return field_names
