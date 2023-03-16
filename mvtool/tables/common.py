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

from typing import Any, Generator, Generic, Iterable, Iterator, NamedTuple, TypeVar

import pandas as pd
from pydantic import BaseModel

from ..utils.errors import ValueHttpError

E = TypeVar("E", bound=BaseModel)  # Export model
I = TypeVar("I", bound=BaseModel)  # Import model


class MissingColumnsError(ValueHttpError):
    def __init__(self, missing_labels: set[str]) -> None:
        self.missing_labels = missing_labels
        super().__init__(f"Missing columns: {', '.join(missing_labels)}")


class Cell(NamedTuple):
    label: str
    value: Any


class Column:
    IMPORT_EXPORT = 0
    IMPORT_ONLY = 1
    EXPORT_ONLY = 2

    def __init__(
        self,
        label: str,
        attr_name: str,
        mode: int | None = None,
        required: bool = False,  # only used for import
        hidden: bool = False,  # only used for export
    ):
        self.label = label
        self.attr_name = attr_name
        self._mode = mode or self.IMPORT_EXPORT
        self.required = required
        self.hidden = hidden

    @property
    def is_export(self) -> bool:
        return (not self.hidden) and self._mode in (
            self.IMPORT_EXPORT,
            self.EXPORT_ONLY,
        )

    @property
    def is_import(self) -> bool:
        return self._mode in (self.IMPORT_EXPORT, self.IMPORT_ONLY)


class ColumnGroup(Generic[I, E]):
    def __init__(
        self,
        import_model: type[I],
        label: str,
        children: "list[Column | ColumnGroup]",
        attr_name: str | None = None,  # must be set if this is a child
    ):
        self.import_model = import_model
        self.label = label
        self.children = children
        self.attr_name = attr_name

    @property
    def is_export(self) -> bool:
        for _ in self.children_for_export:
            return True
        return False

    @property
    def is_import(self) -> bool:
        for _ in self.children_for_import:
            return True
        return False

    @property
    def children_for_export(self) -> "Generator[Column | ColumnGroup]":
        return (c for c in self.children if c.is_export)

    @property
    def children_for_import(self) -> "Generator[Column | ColumnGroup]":
        return (c for c in self.children if c.is_import)

    @property
    def labels_for_export(self) -> "Generator[str]":
        for child in self.children_for_export:
            if isinstance(child, ColumnGroup):
                yield from child.labels_for_export
            else:
                yield f"{self.label} {child.label}"

    def hide_columns(self, labels: list[str]) -> None:
        for child in self.children:
            if isinstance(child, ColumnGroup):
                child.hide_columns(labels)
            else:
                child.hidden = f"{self.label} {child.label}" in labels

    def export_to_row(self, obj: E) -> Iterator[Cell]:
        for child in self.children_for_export:
            value = getattr(obj, child.attr_name)
            if isinstance(child, ColumnGroup):
                if value is not None:  # when value is not None, it must be an object
                    yield from child.export_to_row(value)
            else:
                if value is not None and value != "":
                    yield Cell(f"{self.label} {child.label}", value)

    def export_to_dataframe(self, objs: Iterable[E]) -> pd.DataFrame:
        df = pd.DataFrame(dict(self.export_to_row(o)) for o in objs)

        # reorder columns
        labels_in_df = df.columns.to_list()
        ordered_labels = [l for l in self.labels_for_export if l in labels_in_df]
        return df[ordered_labels]

    def import_from_row(self, row: Iterable[Cell]) -> I:
        row = tuple(row)  # make sure we can iterate multiple times
        column_defs: dict[str, Column] = {}  # associate cell labels and column defs
        required_labels: set[str] = set()  # required labels
        columns_defs: list[ColumnGroup] = []  # subordinated columns defs (nodes)

        for child in self.children_for_import:
            if isinstance(child, Column):
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
                raise MissingColumnsError(missing_labels)

            # proceed with subordinated columns defs (nodes)
            for columns_def in columns_defs:
                model_kwargs[columns_def.attr_name] = columns_def.import_from_row(row)

            return self.import_model(**model_kwargs)  # TODO: handle validation errors

    def import_from_dataframe(self, df: pd.DataFrame) -> Iterator[I]:
        lables = df.columns.to_list()
        for values in df.itertuples(index=False):
            yield self.import_from_row(
                Cell(l, v) for l, v in zip(lables, values) if not pd.isna(v)
            )
