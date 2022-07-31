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
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl import Workbook
from mvtool.models import RequirementInput
from mvtool.views.export import get_excel_temp_file

from mvtool.views.requirements import RequirementsView

router = APIRouter()

@cbv(router)
class ImportRequirementsView:
    kwargs = dict(tags=['requirement'])

    def __init__(self,
            temp_file: NamedTemporaryFile = Depends(get_excel_temp_file),
            requirements: RequirementsView = Depends(RequirementsView)):
        self._temp_file = temp_file
        self._requirements = requirements

    def read_requirement_from_excel_worksheet(self, worksheet: Worksheet):
        headers = {
            'Reference', 'Summary', 'Description', 'Target Object', 
            'Compliance Status', 'Compliance Comment'}
        
        for index, values in enumerate(worksheet.iter_rows(values_only=True)):
            # check and process header row
            if index == 0:
                # check if headers is subset of set(values)
                if not headers.issubset(set(values)):
                    raise ValueError('Invalid header row')
                headers = tuple(values)
                continue
            
            # process data row
            requirement_data = dict(zip(headers, values))
            # TODO: catch validation error
            yield RequirementInput(
                reference=requirement_data['Reference'] or None,
                summary=requirement_data['Summary'],
                description=requirement_data['Description'] or None,
                target_object=requirement_data['Target Object'] or None,
                compliance_status=requirement_data['Compliance Status'] or None,
                compliance_comment=requirement_data['Compliance Comment'] or None)
