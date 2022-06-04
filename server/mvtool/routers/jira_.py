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

from jira import JIRA
from pydantic import BaseModel
from fastapi import Depends, APIRouter, HTTPException
from sqlmodel import Session, select
from ..database import get_session
from ..auth import get_jira

router = APIRouter(prefix='/api/jira')


class JiraProject(BaseModel, orm_mode=True):
    id: str
    key: str
    name: str


class JiraIssue(BaseModel, orm_mode=True):
    id: str


@router.get('/projects', response_model=list[JiraProject])
def get_jira_projects(jira: JIRA = Depends(get_jira)):
    for p in jira.projects():
        yield JiraProject.from_orm(p)

@router.get('/projects/{id}', response_model=JiraProject)
def get_jira_project(id: str, jira: JIRA = Depends(get_jira)) -> JiraProject:
    p = jira.project(id)
    return JiraProject.from_orm(p)