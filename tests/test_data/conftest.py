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

import pytest
from sqlmodel import Session

from mvtool import database
from mvtool.data.catalog_modules import CatalogModules
from mvtool.data.catalog_requirements import CatalogRequirements
from mvtool.data.catalogs import Catalogs
from mvtool.data.projects import Projects
from mvtool.models.catalog_modules import CatalogModuleInput
from mvtool.models.catalogs import CatalogInput


@pytest.fixture
def session(config) -> Session:
    database.setup_engine(config.database)
    database.create_all()

    for session in database.get_session():
        yield session

    database.drop_all()
    database.dispose_engine()


@pytest.fixture
def catalogs(session: Session):
    return Catalogs(session, None)


@pytest.fixture
def catalog_modules(session: Session, catalogs: Catalogs):
    return CatalogModules(catalogs, session)


@pytest.fixture
def catalog_requirements(session: Session, catalog_modules: CatalogModules):
    return CatalogRequirements(catalog_modules, session)


@pytest.fixture
def projects(session: Session, jira_projects):
    return Projects(jira_projects, session)


@pytest.fixture
def catalog(catalogs: Catalogs):
    catalog_input = CatalogInput(reference="ref", title="title")
    return catalogs.create_catalog(catalog_input)


@pytest.fixture
def catalog_module(catalog_modules: CatalogModules, catalog):
    catalog_module_input = CatalogModuleInput(reference="ref", title="title")
    return catalog_modules.create_catalog_module(catalog, catalog_module_input)
