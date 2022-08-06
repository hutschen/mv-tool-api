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

from mvtool.database import CRUDOperations
from mvtool.models import Document, Measure, Project, Requirement


def test_delete_requirements_of_project(crud: CRUDOperations):
    project = Project(name="test")
    project.requirements = [Requirement(summary="test")]
    crud.create_in_db(project)
    crud.session.commit()

    crud.delete_from_db(Project, project.id)
    crud.session.commit()

    assert crud.session.query(Project).count() == 0
    assert crud.session.query(Requirement).count() == 0


def test_delete_documents_of_project(crud: CRUDOperations):
    project = Project(name="test")
    project.documents = [Document(title="test")]
    crud.create_in_db(project)
    crud.session.commit()

    crud.delete_from_db(Project, project.id)
    crud.session.commit()

    assert crud.session.query(Project).count() == 0
    assert crud.session.query(Document).count() == 0


def test_delete_measures_of_requirement(crud: CRUDOperations):
    requirement = Requirement(summary="test")
    requirement.measures = [Measure(summary="test")]
    crud.create_in_db(requirement)
    crud.session.commit()

    crud.delete_from_db(Requirement, requirement.id)
    crud.session.commit()

    assert crud.session.query(Requirement).count() == 0
    assert crud.session.query(Measure).count() == 0


def test_keep_document_of_when_delete_measure(crud: CRUDOperations):
    measure = Measure(summary="test")
    measure.document = Document(title="test")
    crud.create_in_db(measure)
    crud.session.commit()

    crud.delete_from_db(Measure, measure.id)
    crud.session.commit()

    assert crud.session.query(Measure).count() == 0
    assert crud.session.query(Document).count() == 1
