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

from . import (
    catalog_modules,
    catalog_requirements,
    catalogs,
    documents,
    handlers,
    measures,
    projects,
    requirements,
)

router = APIRouter()
router.include_router(handlers.router)
router.include_router(catalogs.router)
router.include_router(catalog_modules.router)
router.include_router(catalog_requirements.router)
router.include_router(projects.router)
router.include_router(requirements.router)
router.include_router(documents.router)
router.include_router(measures.router)
