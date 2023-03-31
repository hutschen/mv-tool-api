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

from typing import Generic, Iterable, Iterator, TypeVar

T = TypeVar("T")


class CachedIterable(Generic[T]):
    """A caching iterable that allows multiple iterations over any iterable.
    The first iteration caches the elements, and subsequent iterations
    use the cached elements.
    """

    def __init__(self, iterable: Iterable[T]):
        self.iterable = iter(iterable)
        self.cache = []

    def __iter__(self) -> Iterator[T]:
        for item in self.cache:
            yield item

        # use a while loop cause iter is already called in __init__
        while True:
            try:
                item = next(self.iterable)
            except StopIteration:
                break
            self.cache.append(item)
            yield item
