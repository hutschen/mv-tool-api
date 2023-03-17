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

from typing import (
    Any,
    Collection,
    Generator,
    Generic,
    Iterable,
    Iterator,
    NamedTuple,
    TypeVar,
)

import pandas as pd
from pydantic import BaseModel, ValidationError

from ..utils.errors import ValueHttpError

E = TypeVar("E", bound=BaseModel)  # Export model
I = TypeVar("I", bound=BaseModel)  # Import model


class MissingColumnsError(ValueHttpError):
    def __init__(self, missing_labels: set[str]) -> None:
        self.missing_labels = missing_labels
        super().__init__(f"Missing columns: {', '.join(missing_labels)}")


class RowValidationError(ValueHttpError):
    def __init__(
        self, column_group: "ColumnGroup", validation_error: ValidationError
    ) -> None:
        columns = {c.attr_name: c for c in column_group.columns if c.attr_name}
        messages = []

        for error in validation_error.errors():
            attr_name = error["loc"][0]
            message = error["msg"]
            column = columns.get(attr_name, None)
            if column is not None:
                messages.append(f'Invalid value in "{column.label}": f{message}')
            else:
                messages.append(message)

        super().__init__(messages)


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
        hidden: bool = False,  # only used for export and not required import columns
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
        not_hidden = self.required or not self.hidden
        return not_hidden and self._mode in (self.IMPORT_EXPORT, self.IMPORT_ONLY)


class ColumnGroup(Generic[I, E]):
    def __init__(
        self,
        import_model: type[I],
        label: str,
        columns: "list[Column | ColumnGroup]",
        attr_name: str | None = None,  # must be set if this is part of another group
    ):
        self.import_model = import_model
        self.label = label
        self.columns = columns
        self.attr_name = attr_name

    @property
    def is_export(self) -> bool:
        for _ in self.export_columns:
            return True
        return False

    @property
    def is_import(self) -> bool:
        for _ in self.import_columns:
            return True
        return False

    @property
    def export_columns(self) -> "Generator[Column | ColumnGroup]":
        return (c for c in self.columns if c.is_export)

    @property
    def import_columns(self) -> "Generator[Column | ColumnGroup]":
        return (c for c in self.columns if c.is_import)

    @property
    def export_labels(self) -> "Generator[str]":
        for column in self.export_columns:
            if isinstance(column, Column):
                yield f"{self.label} {column.label}"
            else:
                yield from column.export_labels

    @property
    def import_labels(self) -> "Generator[str]":
        for column in self.import_columns:
            if isinstance(column, Column):
                yield f"{self.label} {column.label}"
            else:
                yield from column.import_labels

    def hide_columns(self, labels: Collection[str] | None = None) -> None:
        labels = labels or []  # passing None unhides all columns
        for column in self.columns:
            if isinstance(column, Column):
                column.hidden = f"{self.label} {column.label}" in labels
            else:
                column.hide_columns(labels)

    def export_to_row(self, obj: E) -> Iterator[Cell]:
        for column in self.export_columns:
            value = getattr(obj, column.attr_name)
            if isinstance(column, ColumnGroup):
                if value is not None:  # when value is not None, it must be an object
                    yield from column.export_to_row(value)
            else:
                if value is not None and value != "":
                    yield Cell(f"{self.label} {column.label}", value)

    def export_to_dataframe(self, objs: Iterable[E]) -> pd.DataFrame:
        df = pd.DataFrame(dict(self.export_to_row(o)) for o in objs)
        ordered_labels = [l for l in self.export_labels if l in df.columns.to_list()]
        return df[ordered_labels]

    def import_from_row(self, row: Iterable[Cell]) -> I:
        row = tuple(row)  # make sure we can iterate multiple times
        columns: dict[str, Column] = {}  # associate cell labels and columns
        required_labels: set[str] = set()  # required labels
        column_groups: list[ColumnGroup] = []  # subordinated columns groups (nodes)

        for column in self.import_columns:
            if isinstance(column, Column):
                label = f"{self.label} {column.label}"
                columns[label] = column
                if column.required:
                    required_labels.add(label)
            else:
                column_groups.append(column)

        model_kwargs = {}  # kwargs for the model constructor

        existing_labels = set()
        for cell in row:
            column = columns.get(cell.label, None)
            if column:
                existing_labels.add(cell.label)
                model_kwargs[column.attr_name] = cell.value

        if model_kwargs:
            # check if all required labels (columns) are present
            missing_labels = required_labels - existing_labels
            if missing_labels:
                raise MissingColumnsError(missing_labels)

            # proceed with subordinated column groups (nodes)
            for column_group in column_groups:
                model_kwargs[column_group.attr_name] = column_group.import_from_row(row)

            try:
                return self.import_model(**model_kwargs)
            except ValidationError as e:
                raise RowValidationError(self, e)

    def import_from_dataframe(self, df: pd.DataFrame) -> Iterator[I]:
        lables = df.columns.to_list()
        for values in df.itertuples(index=False):
            yield self.import_from_row(
                Cell(l, v) for l, v in zip(lables, values) if not pd.isna(v)
            )
