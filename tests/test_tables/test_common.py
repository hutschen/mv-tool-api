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


def create_person_column_group():
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
def person_column_group() -> ColumnGroup[Person, Person]:
    return create_person_column_group()


@pytest.mark.parametrize(
    "column,is_export,is_import,required,hidden",
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
def test_column(column, is_export, is_import, required, hidden):
    assert column.is_export == is_export
    assert column.is_import == is_import
    assert column.required == required
    assert column.hidden == hidden


@pytest.mark.parametrize(
    "column_group,is_export,is_import,child_labels_export,child_lables_import",
    [
        (
            create_person_column_group(),
            True,
            True,
            ["Name", "Age", "Address"],
            ["Name", "Age", "Address"],
        ),
        (ColumnGroup(Person, "Person", []), False, False, [], []),
        (
            ColumnGroup(Person, "Person", [Column("Name", "name", Column.EXPORT_ONLY)]),
            True,
            False,
            ["Name"],
            [],
        ),
        (
            ColumnGroup(Person, "Person", [Column("Name", "name", Column.IMPORT_ONLY)]),
            False,
            True,
            [],
            ["Name"],
        ),
    ],
)
def test_column_group(
    column_group: ColumnGroup,
    is_export,
    is_import,
    child_labels_export,
    child_lables_import,
):
    assert column_group.is_export == is_export
    assert column_group.is_import == is_import
    assert [c.label for c in column_group.export_columns] == child_labels_export
    assert [c.label for c in column_group.import_columns] == child_lables_import


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
    person_column_group: ColumnGroup[Person, Person],
    person: Person,
    labels: list[str],
):
    cells = person_column_group.export_to_row(person)
    assert [cell.label for cell in cells] == labels


def test_export_to_dataframe(
    person_column_group: ColumnGroup[Person, Person], persons: list[Person]
):
    df = person_column_group.export_to_dataframe(persons)
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
    person_column_group: ColumnGroup[Person, Person], person: Person
):
    cells = person_column_group.export_to_row(person)
    imported_person = person_column_group.import_from_row(cells)
    assert person.dict() == imported_person.dict()


def test_import_from_dataframe(
    person_column_group: ColumnGroup[Person, Person], persons: list[Person]
):
    df = person_column_group.export_to_dataframe(persons)
    imported_persons = person_column_group.import_from_dataframe(df)
    assert [person.dict() for person in persons] == [
        person.dict() for person in imported_persons
    ]
