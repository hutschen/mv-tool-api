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

from tempfile import NamedTemporaryFile
from typing import Iterator
from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse
from fastapi_utils.cbv import cbv
from openpyxl import Workbook
from openpyxl.worksheet.table import Table

from ..database import CRUDOperations
from .projects import ProjectsView
from ..models import RequirementInput, Requirement, RequirementOutput

router = APIRouter()


@cbv(router)
class RequirementsView:
    kwargs = dict(tags=['requirement'])

    def __init__(self,
            projects: ProjectsView = Depends(ProjectsView),
            crud: CRUDOperations[Requirement] = Depends(CRUDOperations)):
        self._projects = projects
        self._crud = crud

    @router.get(
        '/projects/{project_id}/requirements', 
        response_model=list[RequirementOutput], **kwargs)
    def _list_requirements(
            self, project_id: int) -> Iterator[RequirementOutput]:
        project_output = self._projects._get_project(project_id)
        for requirement in self.list_requirements(project_id):
            yield RequirementOutput.from_orm(
                requirement, update=dict(project=project_output))

    def list_requirements(self, project_id: int) -> list[Requirement]:
        return self._crud.read_all_from_db(Requirement, project_id=project_id)

    @router.post(
        '/projects/{project_id}/requirements', status_code=201, 
        response_model=RequirementOutput, **kwargs)
    def _create_requirement(
            self, project_id: int, 
            requirement_input: RequirementInput) -> RequirementOutput:
        return RequirementOutput.from_orm(
            self.create_requirement(project_id, requirement_input),
            update=dict(project=self._projects._get_project(project_id)))

    def create_requirement(
            self, project_id: int, 
            requirement_input: RequirementInput) -> Requirement:
        requirement = Requirement.from_orm(requirement_input)
        requirement.project = self._projects.get_project(project_id)
        return self._crud.create_in_db(requirement)

    @router.get(
        '/requirements/{requirement_id}', 
        response_model=RequirementOutput, **kwargs)
    def _get_requirement(self, requirement_id: int) -> RequirementOutput:
        requirement = self.get_requirement(requirement_id)
        return RequirementOutput.from_orm(requirement, update=dict(
            project=self._projects._get_project(requirement.project_id)))

    def get_requirement(self, requirement_id: int) -> Requirement:
        return self._crud.read_from_db(Requirement, requirement_id)

    @router.put(
        '/requirements/{requirement_id}', 
        response_model=RequirementOutput, **kwargs)
    def _update_requirement(
            self, requirement_id: int,
            requirement_input: RequirementInput) -> RequirementOutput:
        requirement = self.update_requirement(requirement_id, requirement_input)
        return RequirementOutput.from_orm(requirement, update=dict(
            project=self._projects._get_project(requirement.project_id)))

    def update_requirement(
            self, requirement_id: int, 
            requirement_input: RequirementInput) -> Requirement:
        requirement = self._crud.read_from_db(Requirement, requirement_id)
        updated_requirement = Requirement.from_orm(
            requirement_input, update=dict(project_id=requirement.project_id))
        return self._crud.update_in_db(requirement_id, updated_requirement)

    @router.delete(
        '/requirements/{requirement_id}', status_code=204, 
        response_class=Response, **kwargs)
    def delete_requirement(self, requirement_id: int) -> None:
        return self._crud.delete_from_db(Requirement, requirement_id)

    @router.get(
        '/projects/{project_id}/requirements/excel', 
        response_class=FileResponse, **kwargs)
    def export_requirements_excel(
            self, project_id: int, sheet_name: str='Export', 
            filename: str ='export.xlsx') -> FileResponse:
        
        # set up worksheet
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = sheet_name

        # write data
        column_names = [
            'Reference', 'Summary', 'Description', 'Target Object', 
            'Compliance Status', 'Compliance Comment', 'Completion']
        worksheet.append(column_names)
        for requirement in self.list_requirements(project_id):
            worksheet.append([
                requirement.reference, requirement.summary, 
                requirement.description, requirement.target_object,
                requirement.compliance_status, requirement.compliance_comment,
                requirement.completion
            ])

        # create table
        table = Table(displayName=sheet_name, ref=worksheet.calculate_dimension())
        worksheet.add_table(table)

        # save to temporary file and return response
        with NamedTemporaryFile(suffix='.xlsx') as temp_excel_file:
            workbook.save(temp_excel_file.name)
            return FileResponse(
                temp_excel_file.name,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                filename=filename)