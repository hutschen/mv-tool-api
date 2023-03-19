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

from mvtool.models.common import EqualityMixin

# Test models using the EqualityMixin
class Address(EqualityMixin):
    street: str
    city: str
    country: str


class Person(EqualityMixin):
    name: str
    age: int
    address: Address


@pytest.fixture
def address():
    return Address(street="123 Main St", city="New York", country="USA")


@pytest.fixture
def person(address):
    return Person(name="John Doe", age=30, address=address)


def test_equality_mixin_same_instance(address):
    assert address == address


def test_equality_mixin_same_values(address):
    other_address = Address(street="123 Main St", city="New York", country="USA")
    assert address == other_address


def test_equality_mixin_different_values(address):
    other_address = Address(street="456 Market St", city="San Francisco", country="USA")
    assert address != other_address


def test_equality_mixin_nested_same_instance(person):
    assert person == person


def test_equality_mixin_nested_same_values(person, address):
    other_person = Person(name="John Doe", age=30, address=address)
    assert person == other_person


def test_equality_mixin_nested_different_values(person):
    other_address = Address(street="456 Market St", city="San Francisco", country="USA")
    other_person = Person(name="Jane Doe", age=30, address=other_address)
    assert person != other_person


def test_equality_mixin_different_types(address, person):
    assert address != person
