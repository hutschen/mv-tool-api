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
from mvtool.utils.iteration import CachedIterable


def test_cached_iterable_basic():
    iterable = CachedIterable(range(5))
    first_iteration = list(iterable)
    second_iteration = list(iterable)

    assert first_iteration == [0, 1, 2, 3, 4]
    assert second_iteration == [0, 1, 2, 3, 4]


def test_cached_iterable_partial_first_iteration():
    iterable = CachedIterable(range(5))

    # Perform a partial first iteration
    partial_first_iteration = []
    for i, item in enumerate(iterable):
        partial_first_iteration.append(item)
        if i == 2:
            break

    # Perform a second iteration
    second_iteration = list(iterable)

    assert partial_first_iteration == [0, 1, 2]
    assert second_iteration == [0, 1, 2, 3, 4]


def test_cached_iterable_empty():
    iterable = CachedIterable([])
    first_iteration = list(iterable)
    second_iteration = list(iterable)

    assert first_iteration == []
    assert second_iteration == []


@pytest.fixture
def generator():
    def generator():
        for i in range(5):
            yield i

    return generator()


def test_cached_iterable_generated(generator):
    iterable = CachedIterable(generator)
    first_iteration = list(iterable)
    second_iteration = list(iterable)

    assert first_iteration == [0, 1, 2, 3, 4]
    assert second_iteration == [0, 1, 2, 3, 4]


def test_cached_iterable_partial_first_iteration_generated(generator):
    iterable = CachedIterable(generator)

    # Perform a partial first iteration
    partial_first_iteration = []
    for i, item in enumerate(iterable):
        partial_first_iteration.append(item)
        if i == 2:
            break

    # Perform a second iteration
    second_iteration = list(iterable)

    assert partial_first_iteration == [0, 1, 2]
    assert second_iteration == [0, 1, 2, 3, 4]


@pytest.fixture
def interrupted_generator():
    def generator():
        for i in range(5):
            if i == 3:
                raise Exception("Interrupted")
            yield i

    return generator()


def test_cached_iterable_interrupted_first_iteration(interrupted_generator):
    iterable = CachedIterable(interrupted_generator)

    # Perform a first iteration that gets interrupted
    with pytest.raises(Exception, match="Interrupted"):
        for _ in iterable:
            pass

    # Perform a second iteration
    second_iteration = list(iterable)

    assert second_iteration == [0, 1, 2]
