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

from typing import Any, Iterable, NamedTuple


class Cell(NamedTuple):
    label: str
    value: Any


Row = Iterable[Cell]


class DataFrame:
    def __init__(self, rows: Iterable[Row] = None):
        rows = rows or []
        self.data = {}

        for row in rows:
            column_names = set(self.data.keys())
            labels = set()

            # Fill in values
            for chell in row:
                try:
                    self.data[chell.label].append(chell.value)
                except KeyError:
                    self.data[chell.label] = [chell.value]
                labels.add(chell.label)

            # Fill in None for missing values
            for column_name in column_names - labels:
                self.data[column_name].append(None)

    @property
    def column_names(self) -> list[str]:
        return list(self.data.keys())

    def __getitem__(self, column_names: Iterable[str] | str) -> list[Any]:
        column_names = [column_names] if isinstance(column_names, str) else column_names
        df = DataFrame()
        df.data = {column_name: self.data[column_name] for column_name in column_names}
        return df
