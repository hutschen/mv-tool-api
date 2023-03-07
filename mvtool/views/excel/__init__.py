# coding: utf-8
#
# Copyright (C) 2023 Helmar Hutschenreuter
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

from fastapi import APIRouter

from mvtool.views.excel import catalogs, requirements, measures, documents


router = APIRouter()
router.include_router(catalogs.router)  # TODO: use prefix="/excel"
router.include_router(requirements.router)  # TODO: use prefix="/excel"
router.include_router(measures.router)  # TODO: use prefix="/excel"
router.include_router(documents.router)  # TODO: use prefix="/excel"
