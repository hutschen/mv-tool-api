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
from fastapi import Depends, APIRouter, HTTPException
from sqlmodel import Session, select
from ..database import get_session
from ..auth import get_jira
from ..schemas import JiraProject, JiraProjectInput

router = APIRouter(prefix='/api/jira-projects')

@router.get('/', response_model=list[JiraProject])
def get_jira_projects(
        session: Session = Depends(get_session),
        jira: JIRA = Depends(get_jira)) -> list:
    query = select(JiraProject)
    return session.exec(query).all()

@router.post('/', status_code=201, response_model=JiraProject)
def create_jira_project(
        jira_project_input: JiraProjectInput, 
        session: Session = Depends(get_session)) -> JiraProject:
    jira_project = JiraProject.from_orm(jira_project_input)
    session.add(jira_project)
    session.commit()
    session.refresh(jira_project)
    return jira_project

@router.get('/{id}', response_model=JiraProject)
def get_jira_project(id: int, session: Session = Depends(get_session)) -> JiraProject:
    jira_project = session.get(JiraProject, id)
    if jira_project:
        return jira_project
    else:
        raise HTTPException(404, f'No JIRA project with id={id}')

@router.put('/{id}', response_model=JiraProject)
def update_jira_project(
        id: int, jira_project_input: JiraProjectInput,
        session: Session = Depends(get_session)) -> JiraProject:
    jira_project = get_jira_project(id, session)
    jira_project_updated = JiraProject.from_orm(jira_project_input)
    jira_project_updated.id = id
    session.merge(jira_project_updated)
    session.commit()
    return jira_project

@router.delete('/{id}', status_code=204)
def delete_jira_project(
        id: int, session: Session = Depends(get_session)) -> None:
    jira_project = get_jira_project(id, session)
    session.delete(jira_project)
    session.commit()