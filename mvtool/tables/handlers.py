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

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse

from ..auth.jira_ import get_jira
from ..utils.temp_file import copy_upload_to_temp_file, get_temp_file
from .columns import ColumnGroup
from .dataframe import DataFrame
from .rw_csv import (
    CSVDialect,
    EncodingOption,
    get_encoding_options,
    read_csv,
    sniff_csv_dialect,
    write_csv,
)
from .rw_excel import read_excel, write_excel


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


def get_dataframe_from_uploaded_excel(
    temp_file=Depends(copy_upload_to_temp_file),
) -> DataFrame:
    return read_excel(temp_file)


def get_dataframe_from_uploaded_csv(
    temp_file=Depends(copy_upload_to_temp_file),
    encoding: str = "utf-8-sig",
    sniff_dialect: bool = True,
    dialect=Depends(CSVDialect),
) -> DataFrame:
    if sniff_dialect:
        dialect = sniff_csv_dialect(temp_file, encoding, dialect.delimiter)
    return read_csv(temp_file, encoding, dialect)


def get_uploaded_dataframe_handler(format: str) -> Callable:
    if format == "excel":
        return get_dataframe_from_uploaded_excel
    elif format == "csv":
        return get_dataframe_from_uploaded_csv
    else:
        raise ValueError(f"Unknown format: {format}")


def get_download_excel_handler(
    get_dataframe: Callable, sheet_name="Data", filename="data.xlsx"
) -> Callable:
    def handler(
        df: DataFrame = Depends(get_dataframe),
        temp_file=Depends(get_temp_file(".xlsx")),
        sheet_name=sheet_name,
        filename=filename,
    ) -> FileResponse:
        write_excel(df, temp_file, sheet_name)
        return FileResponse(temp_file.name, filename=filename)

    return handler


def get_download_csv_handler(
    get_dataframe: Callable,
    filename="data.csv",
) -> Callable:
    def handler(
        df: DataFrame = Depends(get_dataframe),
        temp_file=Depends(get_temp_file(".csv")),
        filename=filename,
        encoding="utf-8-sig",
        dialect=Depends(CSVDialect),
    ) -> FileResponse:
        write_csv(df, temp_file, encoding, dialect)
        response = FileResponse(temp_file.name, filename=filename)
        response.headers[
            "Content-Type"
        ] = "application/octet-stream"  # Enforce download
        return response

    return handler


router = APIRouter(tags=["common"])


@router.get("/common/encodings", response_model=list[EncodingOption])
def get_supported_encodings(response: Response):
    response.headers["Cache-Control"] = f"public, max-age={60 * 60 * 24 * 7}"  # 7 days
    return get_encoding_options()
