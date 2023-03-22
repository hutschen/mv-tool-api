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
from ..utils.iteration import CachedIterable

E = TypeVar("E", bound=BaseModel)  # Export model
I = TypeVar("I", bound=BaseModel)  # Import model


class MissingColumnsError(ValueHttpError):
    """Exception raised when there are missing columns in the input data.

    Attributes:
        missing_labels (set[str]): Set of missing column labels.
    """

    def __init__(self, missing_labels: set[str]) -> None:
        self.missing_labels = missing_labels
        super().__init__(f"Missing columns: {', '.join(missing_labels)}")


class RowValidationError(ValueHttpError):
    """Exception raised when there is a validation error in a row.

    Attributes:
        column_group (ColumnGroup): The column group associated with the validation error.
        validation_error (ValidationError): The validation error from Pydantic.
    """

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
    """Represents a cell in a table.

    Attributes:
        label (str): The label of the cell.
        value (Any): The value of the cell.
    """

    label: str
    value: Any


class Column:
    """Represents a single column in a table.

    Attributes:
        label (str): The label of the column.
        attr_name (str): The attribute name associated with the column.
        mode (int | None): The mode of the column (import/export, import only, or export only).
        required (bool): Whether the column is required for import (default: False).
        hidden (bool): Whether the column is hidden for export and not required for import columns (default: False).
    """

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
        """Check if the column is an export column.

        A column is considered an export column if it's not hidden and its mode
        is either IMPORT_EXPORT or EXPORT_ONLY.

        Returns:
            bool: True if the column is an export column, False otherwise.
        """
        return (not self.hidden) and self._mode in (
            self.IMPORT_EXPORT,
            self.EXPORT_ONLY,
        )

    @property
    def is_import(self) -> bool:
        """Check if the column is an import column.

        A column is considered an import column if it's required or not hidden, and
        its mode is either IMPORT_EXPORT or IMPORT_ONLY.

        Returns:
            bool: True if the column is an import column, False otherwise.
        """
        not_hidden = self.required or not self.hidden
        return not_hidden and self._mode in (self.IMPORT_EXPORT, self.IMPORT_ONLY)


class ColumnGroup(Generic[I, E]):
    """Represents a group of columns in a table.

    Attributes:
        import_model (type[I]): The Pydantic model used for importing data.
        label (str): The label of the column group.
        columns (list[Column | ColumnGroup]): The list of columns and nested column groups.
        attr_name (str | None): The attribute name associated with the column group (must be set if part of another group).
    """

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
        """Check if the column group has any export columns.

        Returns:
            bool: True if the column group has export columns, False otherwise.
        """
        for _ in self.export_columns:
            return True
        return False

    @property
    def is_import(self) -> bool:
        """Check if the column group has any import columns.

        Returns:
            bool: True if the column group has import columns, False otherwise.
        """
        for _ in self.import_columns:
            return True
        return False

    @property
    def export_columns(self) -> "Generator[Column | ColumnGroup]":
        """Yield export columns from the column group.

        Returns:
            Generator[Column | ColumnGroup]: A generator of export columns.
        """
        return (c for c in self.columns if c.is_export)

    @property
    def import_columns(self) -> "Generator[Column | ColumnGroup]":
        """Yield import columns from the column group.

        Returns:
            Generator[Column | ColumnGroup]: A generator of import columns.
        """
        return (c for c in self.columns if c.is_import)

    @property
    def export_labels(self) -> "Generator[str]":
        """Yield labels of export columns in the column group.

        Returns:
            Generator[str]: A generator of labels for export columns.
        """
        for column in self.export_columns:
            if isinstance(column, Column):
                yield f"{self.label} {column.label}"
            else:
                yield from column.export_labels

    @property
    def import_labels(self) -> "Generator[str]":
        """Yield labels of import columns in the column group.

        Returns:
            Generator[str]: A generator of labels for import columns.
        """
        for column in self.import_columns:
            if isinstance(column, Column):
                yield f"{self.label} {column.label}"
            else:
                yield from column.import_labels

    def hide_columns(self, labels: Collection[str] | None = None) -> None:
        """Hide or unhide columns in the column group based on the provided labels.

        Args:
            labels (Collection[str] | None, optional): Collection of labels to hide. Pass None to unhide all columns.
        """
        labels = labels or []  # passing None unhides all columns
        for column in self.columns:
            if isinstance(column, Column):
                column.hidden = f"{self.label} {column.label}" in labels
            else:
                column.hide_columns(labels)

    def export_to_row(self, obj: E) -> Iterator[Cell]:
        """Export the given object to a row of cells using the export columns of the column group.

        Args:
            obj (E): The object to export.

        Returns:
            Iterator[Cell]: An iterator of cells representing a row in a table.
        """
        for column in self.export_columns:
            value = getattr(obj, column.attr_name)
            if isinstance(column, ColumnGroup):
                if value is not None:  # when value is not None, it must be an object
                    yield from column.export_to_row(value)
            else:
                if value is not None and value != "":
                    yield Cell(f"{self.label} {column.label}", value)

    def export_to_dataframe(self, objs: Iterable[E]) -> pd.DataFrame:
        """Export a collection of objects to a Pandas DataFrame using the export columns of the column group.

        Args:
            objs (Iterable[E]): An iterable of objects to export.

        Returns:
            pd.DataFrame: A Pandas DataFrame containing the exported data.
        """
        df = pd.DataFrame(dict(self.export_to_row(o)) for o in objs)
        ordered_labels = [l for l in self.export_labels if l in df.columns.to_list()]
        return df[ordered_labels]

    def import_from_row(self, row: Iterable[Cell]) -> I:
        """Import data from a row of cells using the import columns of the column group and create an instance of the import model.

        Args:
            row (Iterable[Cell]): An iterable of cells representing a row in a table.

        Returns:
            I: An instance of the import model.

        Raises:
            MissingColumnsError: If there are any missing required columns in the row.
            RowValidationError: If there is a validation error while creating the import model instance.
        """
        row = CachedIterable(row)  # make sure we can iterate multiple times
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

        if model_kwargs and not all(v is None for v in model_kwargs.values()):
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

    def import_from_dataframe(self, df: pd.DataFrame, skip_nan=True) -> Iterator[I]:
        """Import data from a Pandas DataFrame using the import columns of the column
        group and create instances of the import model.

        Args:
            df (pd.DataFrame): A Pandas DataFrame containing the data to import.
            skip_nan (bool, optional): Ignore cells with NaN values. Defaults to True.

        Returns:
            Iterator[I]: An iterator of instances of the import model.
        """
        lables = df.columns.to_list()
        for values in df.itertuples(index=False):
            l_v = zip(lables, values)
            if skip_nan:
                row = (Cell(l, v) for l, v in l_v if not pd.isna(v))
            else:
                row = (Cell(l, (None if pd.isna(v) else v)) for l, v in l_v)
            yield self.import_from_row(row)
