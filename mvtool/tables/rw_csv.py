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
import codecs
import csv
from typing import IO

from pydantic import BaseModel, constr, field_validator

from ..utils.errors import ValueHttpError
from .dataframe import DataFrame


class CSVDialect(BaseModel):
    delimiter: constr(min_length=1, max_length=1) = ","
    doublequote: bool = True
    escapechar: constr(min_length=1, max_length=1) | None = None
    lineterminator: constr(pattern="^(\n|\r\n)$") = "\r\n"
    quotechar: constr(min_length=1, max_length=1) = '"'
    quoting: int = csv.QUOTE_MINIMAL
    skipinitialspace: bool = False

    @field_validator("quoting")
    def quoting_validator(cls, value):
        valid_values = [
            csv.QUOTE_ALL,
            csv.QUOTE_MINIMAL,
            csv.QUOTE_NONNUMERIC,
            csv.QUOTE_NONE,
        ]
        if value not in valid_values:
            raise ValueError(f"Invalid quoting value, must be one of {valid_values}")
        return value


def read_csv(
    file_obj: IO[bytes],
    encoding: str = "utf-8-sig",  # Use UTF-8 with BOM by default
    dialect: CSVDialect | None = None,
) -> DataFrame:
    """Read a CSV file and return a DataFrame."""
    csv_file_obj = codecs.getreader(encoding)(file_obj)

    try:
        csv_reader = csv.DictReader(
            csv_file_obj,
            **(dialect.model_dump(exclude_unset=True) if dialect else {}),
            strict=True,
        )

        # Construct a dictionary with lists of values for each column
        data_dict = {key: [] for key in csv_reader.fieldnames}
        for row in csv_reader:
            for key, value in row.items():
                data_dict[key].append(value)
    except UnicodeDecodeError as e:
        raise ValueHttpError(
            f"Error decoding the CSV file using the '{encoding}' encoding: {str(e)}"
        )
    except (csv.Error, KeyError) as e:
        raise ValueHttpError(f"Error reading CSV due to: {str(e)}")

    # Encapsulate data_dict in a DataFrame
    df = DataFrame()
    df.data = data_dict
    return df
