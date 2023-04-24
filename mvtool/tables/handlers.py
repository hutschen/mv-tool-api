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

from typing import Callable

import pandas as pd
from fastapi import Depends, HTTPException, Query

from ..auth import get_jira
from ..utils.temp_file import copy_upload_to_temp_file
from .common import ColumnGroup


def hide_columns(get_columns: Callable) -> Callable:
    def handler(
        hidden_columns: list[str] | None = Query(None),
        columns: ColumnGroup = Depends(get_columns),
    ) -> ColumnGroup:
        columns.hide_columns(hidden_columns)
        return columns

    return handler


def get_export_labels_handler(get_columns: Callable) -> Callable:
    def handler(
        columns: ColumnGroup = Depends(get_columns),
        _=Depends(get_jira),  # get jira to enforce login
    ) -> list[str]:
        return columns.export_labels

    return handler


def get_uploaded_dataframe(
    temp_file=Depends(copy_upload_to_temp_file),
    skip_duplicates: bool = False,
) -> pd.DataFrame:
    # Default list of na_values of pandas without 'N/A'
    na_values = [
        # fmt: off
        "", "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN", "-NaN", "-nan",
        "1.#IND", "1.#QNAN", "<NA>", "NA", "NULL", "NaN", "None", "n/a", "nan", "null"
        # fmt: on
    ]

    try:
        df = pd.read_excel(
            temp_file, engine="openpyxl", keep_default_na=False, na_values=na_values
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Invalid file. Only Excel files are supported: " + str(e),
        )

    if skip_duplicates:
        df.drop_duplicates(keep="last", inplace=True)
    return df
