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
from sqlmodel import Session
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from ..auth import get_jira
from ..database import CRUDOperations, get_session
from .measures import MeasuresView
from ..models import TaskInput, Task

router = APIRouter()


@cbv(router)
class TasksView(CRUDOperations[Task]):
    kwargs = dict(tags=['task'])

    def __init__(
            self, session: Session = Depends(get_session),
            jira: JIRA = Depends(get_jira)):
        super().__init__(session, Task)
        self.measures = MeasuresView(session, jira)

    @router.get(
        '/measures/{measure_id}/tasks', response_model=list[Task], **kwargs)
    def list_tasks(self, measure_id: int) -> list[Task]:
        return self.read_all_from_db(measure_id=measure_id)

    @router.post(
        '/measures/{measure_id}/tasks', status_code=201, response_model=Task, 
        **kwargs)
    def create_task(self, measure_id: int, task: TaskInput) -> Task:
        task = Task.from_orm(task)
        task.measure = self.measures.get_measure(measure_id)
        return self.create_in_db(task)

    @router.get('/tasks/{task_id}', response_model=Task, **kwargs)
    def get_task(self, task_id: int) -> Task:
        return self.read_from_db(task_id)

    @router.put('/tasks/{task_id}', response_model=Task, **kwargs)
    def update_task(self, task_id: int, task_update: TaskInput) -> Task:
        task = self.read_from_db(task_id)
        task_update = Task.from_orm(task_update, update=dict(
            measure_id=task.measure_id, jira_issue_id=task.jira_issue_id))
        return self.update_in_db(task_id, task_update)

    @router.delete(
        '/tasks/{task_id}', status_code=204, response_model=None, **kwargs)
    def delete_task(self, task_id: int):
        return self.delete_in_db(task_id)