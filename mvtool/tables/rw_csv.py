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

from ..utils.errors import ValueHttpError
from .dataframe import DataFrame


def read_csv(
    file_obj: IO[bytes],
    encoding: str = "utf-8-sig",  # Use UTF-8 with BOM by default
    **dialect_options,
) -> DataFrame:
    csv_file_obj = codecs.getreader(encoding)(file_obj)

    try:
        csv_reader = csv.DictReader(csv_file_obj, **dialect_options)

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
