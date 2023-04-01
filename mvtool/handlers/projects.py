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
from sqlmodel import Column, or_

from ..data.projects import ProjectsView
from ..models.projects import (
    Project,
    ProjectInput,
    ProjectOutput,
    ProjectRepresentation,
)
from ..utils.filtering import (
    filter_by_pattern,
    filter_by_values,
    filter_for_existence,
    search_columns,
)
from ..utils.pagination import Page, page_params


def get_project_filters(
    # filter by pattern
    name: str | None = None,
    description: str | None = None,
    #
    # filter by ids
    ids: list[int] | None = Query(None),
    jira_project_ids: list[str] | None = Query(None),
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
    for column, value in [
        (Project.name, name),
        (Project.description, description),
    ]:
        if value is not None:
            where_clauses.append(filter_by_pattern(column, value))

    # filter by ids
    for column, values in (
        (Project.id, ids),
        (Project.jira_project_id, jira_project_ids),
    ):
        if values:
            where_clauses.append(filter_by_values(column, values))

    # filter for existence
    for column, value in [
        (Project.description, has_description),
        (Project.jira_project_id, has_jira_project),
    ]:
        if value is not None:
            where_clauses.append(filter_for_existence(column, value))

    # filter by search string
    if search:
        where_clauses.append(
            or_(
                filter_by_pattern(column, f"*{search}*")
                for column in (Project.name, Project.description)
            )
        )

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
    projects_view: ProjectsView = Depends(),
):
    projects = projects_view.list_projects(
        where_clauses, order_by_clauses, **page_params
    )
    if page_params:
        projects_count = projects_view.count_projects(where_clauses)
        return Page[ProjectOutput](items=projects, total_count=projects_count)
    else:
        return projects


@router.post("/projects", status_code=201, response_model=ProjectOutput)
def create_project(
    project: ProjectInput, projects_view: ProjectsView = Depends()
) -> Project:
    return projects_view.create_project(project)


@router.get("/projects/{project_id}", response_model=ProjectOutput)
def get_project(project_id: int, projects_view: ProjectsView = Depends()) -> Project:
    return projects_view.get_project(project_id)


@router.put("/projects/{project_id}", response_model=ProjectOutput)
def update_project(
    project_id: int,
    project_input: ProjectInput,
    projects_view: ProjectsView = Depends(),
) -> Project:
    project = projects_view.get_project(project_id)
    projects_view.update_project(project, project_input)
    return project


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int, projects_view: ProjectsView = Depends()) -> None:
    project = projects_view.get_project(project_id)
    projects_view.delete_project(project)


@router.get(
    "/project/representations",
    response_model=Page[ProjectRepresentation] | list[ProjectRepresentation],
)
def get_project_representations(
    where_clauses: list[Any] = Depends(get_project_filters),
    local_search: str | None = None,
    order_by_clauses=Depends(get_project_sort),
    page_params=Depends(page_params),
    projects_view: ProjectsView = Depends(),
):
    if local_search:
        where_clauses.append(search_columns(local_search, Project.name))

    projects = projects_view.list_projects(
        where_clauses, order_by_clauses, **page_params, query_jira=False
    )
    if page_params:
        projects_count = projects_view.count_projects(where_clauses)
        return Page[ProjectRepresentation](items=projects, total_count=projects_count)
    else:
        return projects


@router.get("/project/field-names", response_model=list[str])
def get_project_field_names(
    where_clauses=Depends(get_project_filters),
    projects_view: ProjectsView = Depends(),
) -> set[str]:
    field_names = {"id", "name"}
    for field, names in [
        (Project.description, ["description"]),
        (Project.jira_project_id, ["jira_project"]),
    ]:
        if projects_view.count_projects(
            [filter_for_existence(field, True), *where_clauses]
        ):
            field_names.update(names)
    return field_names
