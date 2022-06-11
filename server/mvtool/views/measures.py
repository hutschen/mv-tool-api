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
from .requirements import RequirementsView
from ..models import MeasureInput, Measure

router = APIRouter()


@cbv(router)
class MeasuresView(CRUDOperations[Measure]):
    kwargs = dict(tags=['measure'])

    def __init__(
            self, session: Session = Depends(get_session),
            jira: JIRA = Depends(get_jira)):
        super().__init__(session, Measure)
        self.requirements = RequirementsView(session, jira)

    @router.get(
        '/requirements/{requirement_id}/measures', 
        response_model=list[Measure], **kwargs)
    def list_measures(self, requirement_id: int) -> list[Measure]:
        return self.read_all_from_db(requirement_id=requirement_id)

    @router.post(
        '/requirements/{requirement_id}/measures', status_code=201,
        response_model=Measure, **kwargs)
    def create_measure(
            self, requirement_id: int, measure: MeasureInput) -> Measure:
        measure = Measure.from_orm(measure)
        measure.requirement = self.requirements.get_requirement(requirement_id)
        return self.create_in_db(measure)

    @router.get(
        '/measures/{measure_id}', response_model=Measure, **kwargs)
    def get_measure(self, measure_id: int):
        return self.read_from_db(measure_id)