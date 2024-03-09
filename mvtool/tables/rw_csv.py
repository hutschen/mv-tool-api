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
from typing import Annotated, BinaryIO

from pydantic import BaseModel, StringConstraints

from ..utils.errors import ValueHttpError
from ..utils.temp_file import preserved_cursor_position
from .dataframe import DataFrame


class EncodingOption(BaseModel):
    name: str
    encoding: str
    description: str | None = None


def lookup_encoding(encoding: str) -> bool:
    try:
        codecs.lookup(encoding)
        return True
    except LookupError:
        return False


def get_encoding_options() -> list[EncodingOption]:
    """Return a list of encodings to open CSV files with."""
    common_encodings = [
        # fmt: off
        ("UTF-8 (with BOM)", "utf-8-sig", "Unicode 8-bit with Byte Order Mark"),
        ("UTF-8", "utf-8", "Unicode 8-bit"),
        ("UTF-16 (with BOM)", "utf-16", "Unicode 16-bit with Byte Order Mark"),
        ("UTF-16 BE", "utf-16-be", "Unicode 16-bit Big-Endian"),
        ("UTF-16 LE", "utf-16-le", "Unicode 16-bit Little-Endian"),
        ("UTF-32 (with BOM)", "utf-32", "Unicode 32-bit with Byte Order Mark"),
        ("UTF-32 BE", "utf-32-be", "Unicode 32-bit Big-Endian"),
        ("UTF-32 LE", "utf-32-le", "Unicode 32-bit Little-Endian"),
        ("ASCII", "ascii", "American Standard Code for Information Interchange"),
        ("Windows-1252", "cp1252", "Western European (Windows)"),
        ("Windows-1250", "cp1250", "Central European (Windows)"),
        ("Windows-1251", "cp1251", "Cyrillic (Windows)"),
        ("Windows-1253", "cp1253", "Greek (Windows)"),
        ("Windows-1254", "cp1254", "Turkish (Windows)"),
        ("Windows-1255", "cp1255", "Hebrew (Windows)"),
        ("Windows-1256", "cp1256", "Arabic (Windows)"),
        ("Windows-1257", "cp1257", "Baltic (Windows)"),
        ("Windows-1258", "cp1258", "Vietnamese (Windows)"),
        ("Latin-1 (ISO-8859-1)", "latin-1", "Western European"),
        ("ISO-8859-2", "iso8859-2", "Central European"),
        ("ISO-8859-3", "iso8859-3", "South European"),
        ("ISO-8859-4", "iso8859-4", "North European"),
        ("ISO-8859-5", "iso8859-5", "Latin/Cyrillic"),
        ("ISO-8859-6", "iso8859-6", "Latin/Arabic"),
        ("ISO-8859-7", "iso8859-7", "Latin/Greek"),
        ("ISO-8859-8", "iso8859-8", "Latin/Hebrew"),
        ("ISO-8859-9", "iso8859-9", "Turkish"),
        ("ISO-8859-10", "iso8859-10", "Nordic"),
        ("ISO-8859-11", "iso8859-11", "Thai"),
        ("ISO-8859-13", "iso8859-13", "Baltic"),
        ("ISO-8859-14", "iso8859-14", "Celtic"),
        ("ISO-8859-15", "iso8859-15", "Western European with Euro"),
        ("ISO-8859-16", "iso8859-16", "South-Eastern European"),
        ("Big5", "big5", "Traditional Chinese"),
        ("EUC-JP", "euc_jp", "Japanese (Extended Unix Code)"),
        ("EUC-KR", "euc_kr", "Korean (Extended Unix Code)"),
        ("GB2312", "gb2312", "Simplified Chinese"),
        ("GB18030", "gb18030", "Chinese (Simplified + Traditional)"),
        ("Shift_JIS", "shift_jis", "Japanese (Shift Japanese Industrial Standards)"),
        ("KOI8-R", "koi8_r", "Russian (Kod Obmena Informatsiey, 8 bit)"),
        ("KOI8-U", "koi8_u", "Ukrainian (Kod Obmena Informatsiey, 8 bit)"),
        ("MacRoman", "macroman", "Western European (Macintosh)"),
        # fmt: on
    ]

    return [
        EncodingOption(name=name, encoding=encoding, description=description)
        for name, encoding, description in common_encodings
        if lookup_encoding(encoding)
    ]


class CSVDialect(BaseModel):
    delimiter: Annotated[str, StringConstraints(min_length=1, max_length=1)] = ","
    doublequote: bool = True
    escapechar: Annotated[str, StringConstraints(min_length=1, max_length=1)] | None = (
        None
    )
    lineterminator: Annotated[str, StringConstraints(pattern="^(lf|crlf)$")] = "crlf"
    quotechar: Annotated[str, StringConstraints(min_length=1, max_length=1)] = '"'
    quoting: Annotated[
        str, StringConstraints(pattern="^(all|minimal|nonnumeric|none)$")
    ] = "minimal"
    skipinitialspace: bool = False

    @staticmethod
    def _to_lineterminator(value: str) -> str:
        return {
            "lf": "\n",
            "crlf": "\r\n",
        }[value]

    @staticmethod
    def _from_lineterminator(value: str) -> str:
        return {
            "\n": "lf",
            "\r\n": "crlf",
        }[value]

    @staticmethod
    def _to_quoting_literal(value: str) -> int:
        return {
            "all": csv.QUOTE_ALL,
            "minimal": csv.QUOTE_MINIMAL,
            "nonnumeric": csv.QUOTE_NONNUMERIC,
            "none": csv.QUOTE_NONE,
        }[value]

    @staticmethod
    def _from_quoting_literal(value: int) -> str:
        return {
            csv.QUOTE_ALL: "all",
            csv.QUOTE_MINIMAL: "minimal",
            csv.QUOTE_NONNUMERIC: "nonnumeric",
            csv.QUOTE_NONE: "none",
        }[value]

    def to_dialect_kwargs(self):
        kwargs = self.model_dump(exclude_unset=True)
        if "lineterminator" in kwargs:
            kwargs["lineterminator"] = self._to_lineterminator(kwargs["lineterminator"])
        if "quoting" in kwargs:
            kwargs["quoting"] = self._to_quoting_literal(kwargs["quoting"])
        return kwargs

    @classmethod
    def from_dialect_kwargs(cls, **kwargs):
        if "lineterminator" in kwargs:
            kwargs["lineterminator"] = cls._from_lineterminator(
                kwargs["lineterminator"]
            )
        if "quoting" in kwargs:
            kwargs["quoting"] = cls._from_quoting_literal(kwargs["quoting"])
        return cls(**kwargs)


def sniff_csv_dialect(
    file_obj: BinaryIO,
    encoding: str = "utf-8-sig",  # Use UTF-8 with BOM to be compatible with Excel
    delimiters: str | None = ",;",
    sample_size: int = 1024 * 1024,  # 1 MB
) -> CSVDialect:
    """Sniff the CSV dialect of a file."""
    try:
        csv_stream_reader = codecs.getreader(encoding)(file_obj)
    except LookupError:
        raise ValueHttpError(f"Unsupported encoding: {encoding}")

    try:
        with preserved_cursor_position(file_obj):
            dialect = csv.Sniffer().sniff(
                csv_stream_reader.read(sample_size), delimiters
            )
    except UnicodeDecodeError as e:
        raise ValueHttpError(
            f"Error decoding the CSV file using the '{encoding}' encoding: {str(e)}"
        )
    except csv.Error as e:
        raise ValueHttpError(f"Error sniffing CSV dialect due to: {str(e)}")

    if dialect is None:
        raise ValueHttpError("Could not sniff CSV dialect")

    # Convert dialect to CSVDialect
    return CSVDialect.from_dialect_kwargs(
        delimiter=dialect.delimiter,
        doublequote=dialect.doublequote,
        escapechar=dialect.escapechar,
        lineterminator=dialect.lineterminator,
        quotechar=dialect.quotechar,
        quoting=dialect.quoting,
        skipinitialspace=dialect.skipinitialspace,
    )


def read_csv(
    file_obj: BinaryIO,
    encoding: str = "utf-8-sig",  # Use UTF-8 with BOM to be compatible with Excel
    dialect: CSVDialect | None = None,
) -> DataFrame:
    """Read a CSV file and return a DataFrame."""
    try:
        csv_stream_reader = codecs.getreader(encoding)(file_obj)
    except LookupError:
        raise ValueHttpError(f"Unsupported encoding: {encoding}")

    try:
        csv_reader = csv.DictReader(
            csv_stream_reader,
            **(dialect.to_dialect_kwargs() if dialect else {}),
            strict=True,
        )

        with preserved_cursor_position(file_obj):
            # Construct a dictionary with lists of values for each column
            data_dict = {key: [] for key in csv_reader.fieldnames}
            for row in csv_reader:
                for key, value in row.items():
                    data_dict[key].append(
                        # represent empty strings as None
                        None
                        if isinstance(value, str) and value.strip() == ""
                        else value
                    )
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


def write_csv(
    df: DataFrame,
    file_obj: BinaryIO,
    encoding: str = "utf-8-sig",  # Use UTF-8 with BOM to be compatible with Excel
    dialect: CSVDialect | None = None,
):
    """Writes a DataFrame to a CSV file."""
    try:
        csv_stream_writer = codecs.getwriter(encoding)(file_obj)
    except LookupError:
        raise ValueHttpError(f"Unsupported encoding: {encoding}")

    writer = csv.DictWriter(
        csv_stream_writer,
        fieldnames=df.column_names,
        **(dialect.to_dialect_kwargs() if dialect else {}),
    )

    with preserved_cursor_position(file_obj):
        writer.writeheader()
        for row in df:
            writer.writerow({cell.label: cell.value for cell in row})
        file_obj.flush()  # Make sure that all data is written
