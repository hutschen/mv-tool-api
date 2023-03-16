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
from pydantic import BaseModel

from mvtool.tables.common import Column, ColumnGroup


# define example models
class Address(BaseModel):
    street: str
    zip: str
    city: str


class Person(BaseModel):
    name: str
    age: int
    address: Address | None


def create_persons() -> list[Person]:
    return [
        Person(
            name="Alice",
            age=42,
            address=Address(street="Main Street", zip="12345", city="New York"),
        ),
        Person(
            name="Bob",
            age=23,
            address=Address(street="Hillside Drive", zip="12345", city="Los Angeles"),
        ),
        Person(name="Charlie", age=18, address=None),
    ]


@pytest.fixture
def persons() -> list[Person]:
    return create_persons()


def create_person_columns_def():
    return ColumnGroup[Person, Person](
        Person,
        "Person",
        [
            Column("Name", "name", required=True),
            Column("Age", "age"),
            ColumnGroup[Address, Address](
                Address,
                "Address",
                [
                    Column("Street", "street", required=True),
                    Column("ZIP", "zip", required=True),
                    Column("City", "city", required=True),
                ],
                "address",
            ),
        ],
    )


@pytest.fixture
def person_columns_def() -> ColumnGroup[Person, Person]:
    return create_person_columns_def()


@pytest.mark.parametrize(
    "column_def,is_export,is_import,required,hidden",
    [
        (Column("Name", "name"), True, True, False, False),
        (Column("Name", "name", Column.IMPORT_EXPORT), True, True, False, False),
        (Column("Name", "name", Column.IMPORT_ONLY), False, True, False, False),
        (Column("Name", "name", Column.EXPORT_ONLY), True, False, False, False),
        (Column("Name", "name", required=True), True, True, True, False),
        (Column("Name", "name", hidden=True), False, False, False, True),
        (Column("Name", "name", hidden=True, required=True), False, True, True, True),
    ],
)
def test_column_def(column_def, is_export, is_import, required, hidden):
    assert column_def.is_export == is_export
    assert column_def.is_import == is_import
    assert column_def.required == required
    assert column_def.hidden == hidden


@pytest.mark.parametrize(
    "columns_def,is_export,is_import,child_labels_export,child_lables_import,export_labels",
    [
        (
            create_person_columns_def(),
            True,
            True,
            ["Name", "Age", "Address"],
            ["Name", "Age", "Address"],
            [
                "Person Name",
                "Person Age",
                "Address Street",
                "Address ZIP",
                "Address City",
            ],
        ),
        (ColumnGroup(Person, "Person", []), False, False, [], [], []),
        (
            ColumnGroup(Person, "Person", [Column("Name", "name", Column.EXPORT_ONLY)]),
            True,
            False,
            ["Name"],
            [],
            ["Person Name"],
        ),
        (
            ColumnGroup(Person, "Person", [Column("Name", "name", Column.IMPORT_ONLY)]),
            False,
            True,
            [],
            ["Name"],
            [],
        ),
    ],
)
def test_columns_def(
    columns_def: ColumnGroup,
    is_export,
    is_import,
    child_labels_export,
    child_lables_import,
    export_labels,
):
    assert columns_def.is_export == is_export
    assert columns_def.is_import == is_import
    assert [c.label for c in columns_def.export_columns] == child_labels_export
    assert [c.label for c in columns_def.import_columns] == child_lables_import
    assert list(columns_def.export_labels) == export_labels


@pytest.mark.parametrize(
    "person,labels",
    [
        (
            Person(
                name="Bob",
                age=23,
                address=Address(
                    street="Hillside Drive", zip="12345", city="Los Angeles"
                ),
            ),
            [
                "Person Name",
                "Person Age",
                "Address Street",
                "Address ZIP",
                "Address City",
            ],
        ),
        (
            Person(name="Charlie", age=18, address=None),
            ["Person Name", "Person Age"],
        ),
    ],
)
def test_export_to_row(
    person_columns_def: ColumnGroup[Person, Person], person: Person, labels: list[str]
):
    cells = person_columns_def.export_to_row(person)
    assert [cell.label for cell in cells] == labels


def test_export_to_dataframe(
    person_columns_def: ColumnGroup[Person, Person], persons: list[Person]
):
    df = person_columns_def.export_to_dataframe(persons)
    assert df.shape == (3, 5)
    assert df.columns.tolist() == [
        "Person Name",
        "Person Age",
        "Address Street",
        "Address ZIP",
        "Address City",
    ]


@pytest.mark.parametrize("person", create_persons())
def test_import_from_row(
    person_columns_def: ColumnGroup[Person, Person], person: Person
):
    cells = person_columns_def.export_to_row(person)
    imported_person = person_columns_def.import_from_row(cells)
    assert person.dict() == imported_person.dict()


def test_import_from_dataframe(
    person_columns_def: ColumnGroup[Person, Person], persons: list[Person]
):
    df = person_columns_def.export_to_dataframe(persons)
    imported_persons = person_columns_def.import_from_dataframe(df)
    assert [person.dict() for person in persons] == [
        person.dict() for person in imported_persons
    ]
