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
from mvtool.data.documents import Documents
from mvtool.data.jira_ import JiraProjects
from mvtool.data.projects import Projects
from mvtool.data.requirements import Requirements
from mvtool.models.catalog_modules import CatalogModule, CatalogModuleInput
from mvtool.models.catalog_requirements import CatalogRequirementInput
from mvtool.models.catalogs import CatalogInput
from mvtool.models.jira_ import JiraProject
from mvtool.models.projects import ProjectInput


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
def projects(session: Session, jira_projects: JiraProjects):
    return Projects(jira_projects, session)


@pytest.fixture
def requirements(
    session: Session, catalog_requirements: CatalogRequirements, projects: Projects
):
    return Requirements(projects, catalog_requirements, session)


@pytest.fixture
def documents(session: Session, projects: Projects):
    return Documents(projects, session)


@pytest.fixture
def catalog(catalogs: Catalogs):
    catalog_input = CatalogInput(reference="ref", title="title")
    return catalogs.create_catalog(catalog_input)


@pytest.fixture
def catalog_module(catalog_modules: CatalogModules, catalog):
    catalog_module_input = CatalogModuleInput(reference="ref", title="title")
    return catalog_modules.create_catalog_module(catalog, catalog_module_input)


@pytest.fixture
def catalog_requirement(
    catalog_requirements: CatalogRequirements, catalog_module: CatalogModule
):
    catalog_requirement_input = CatalogRequirementInput(
        reference="ref", summary="title"
    )
    return catalog_requirements.create_catalog_requirement(
        catalog_module, catalog_requirement_input
    )


@pytest.fixture
def project(projects: Projects, jira_project: JiraProject):
    project_input = ProjectInput(name="name", jira_project_id=jira_project.id)
    return projects.create_project(project_input)
