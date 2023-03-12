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

from typing import Any, Generic, Iterable, Iterator, NamedTuple, TypeVar

import pandas as pd
from pydantic import BaseModel

E = TypeVar("E", BaseModel)  # Export model
I = TypeVar("I", BaseModel)  # Import model


class MissingLabelsError(ValueError):
    def __init__(self, missing_labels: set[str]) -> None:
        self.missing_labels = missing_labels
        super().__init__(f"Missing labels: {', '.join(missing_labels)}")


class Cell(NamedTuple):
    label: str
    value: Any


class ColumnDef:
    IMPORT_EXPORT = 0
    IMPORT_ONLY = 1
    EXPORT_ONLY = 2

    def __init__(
        self,
        label: str,
        attr_name: str,
        mode: int | None = None,
        required: bool = False,
        hidden: bool = False,  # only used for export
    ):
        self.label = label
        self.attr_name = attr_name
        self._mode = mode or self.IMPORT_EXPORT
        self.required = required
        self._hidden = hidden

    @property
    def is_export(self) -> bool:
        return self._mode in (self.IMPORT_EXPORT, self.EXPORT_ONLY)

    @property
    def is_import(self) -> bool:
        return self._mode in (self.IMPORT_EXPORT, self.IMPORT_ONLY)

    @property
    def hidden(self) -> bool:
        # a column can only be hidden if it is not required
        return (not self.required) and self._hidden

    @hidden.setter
    def hidden(self, value: bool) -> None:
        self._hidden = value


class ColumnsDef(Generic[I, E]):
    def __init__(
        self,
        import_model: type[I],
        label: str,
        children: list[ColumnDef | "ColumnsDef"],
        attr_name: str | None = None,
    ):
        self.import_model = import_model
        self.label = label
        self.children = children
        self.attr_name = attr_name

    @property
    def children_for_export(self) -> list[ColumnDef]:
        return [c for c in self.children if c.is_export]

    @property
    def children_for_import(self) -> list[ColumnDef]:
        return [c for c in self.children if c.is_import]

    @property
    def is_export(self) -> bool:
        return bool(self.children_for_export)

    @property
    def is_import(self) -> bool:
        return bool(self.children_for_import)

    def export_to_row(self, obj: E) -> Iterator[Cell]:
        for child in self.children_for_export:
            value = getattr(obj, child.attr_name)
            if isinstance(child, ColumnsDef):
                if value:
                    yield from child.export_to_row(value)
            else:
                if (value or child.required) and not child.hidden:
                    yield Cell(f"{self.label} {child.label}", value)

    def export_to_dataframe(self, objs: Iterable[E]) -> pd.DataFrame:
        return pd.DataFrame(dict(self.export_to_row(o)) for o in objs)

    def import_from_row(self, row: Iterable[Cell]) -> I:
        column_defs: dict[str, ColumnDef] = {}  # associate cell labels and column defs
        required_labels: set[str] = set()  # required labels
        columns_defs: list[ColumnsDef] = []  # subordinated columns defs (nodes)

        for child in self.children_for_import:
            if isinstance(child, ColumnDef):
                label = f"{self.label} {child.label}"
                column_defs[label] = child
                if child.required:
                    required_labels.add(label)
            else:
                columns_defs.append(child)

        model_kwargs = {}  # kwargs for the model constructor

        existing_labels = set()
        for cell in row:
            column_def = column_defs.get(cell.label, None)
            if column_def:
                existing_labels.add(cell.label)
                model_kwargs[column_def.attr_name] = cell.value

        if model_kwargs:
            # check if all required labels (columns) are present
            missing_labels = required_labels - existing_labels
            if missing_labels:
                raise MissingLabelsError(missing_labels)

            # proceed with subordinated columns defs (nodes)
            for columns_def in columns_defs:
                model_kwargs[columns_def.attr_name] = columns_def.import_from_row(row)

            return self.import_model(**model_kwargs)
