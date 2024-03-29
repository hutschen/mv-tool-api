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

import re
from collections import namedtuple
from dataclasses import dataclass
from typing import Iterable, cast

GS_SCHICHT_TITLE_RE = re.compile(r"^\s*([A-Z]{3,4})\s+(.+?)\s*$")
GS_BAUSTEIN_TITLE_RE = re.compile(r"^\s*([A-Z]{3,4}(\.[0-9]+)+)\s*(.+?)\s*$")
GS_ANFORDERUNG_TITLE_RE_1 = re.compile(
    r"^\s*([A-Z]+(\.[0-9]+)+\.A[0-9]+)\s+([^\]]+?)\s+(\[([^\]]+)\])?\s*\((B|S|H)\)\s*$"
)
GS_ANFORDERUNG_TITLE_RE_2 = re.compile(
    r"^\s*([A-Z]+(\.[0-9]+)+\.A[0-9]+)\s+([^\]]+?)\s+\((B|S|H)\)\s*(\[([^\]]+)\])?\s*$"
)

GS_ANFORDERUNGEN_SECTION_TITLE = "anforderungen"
GS_ANFORDERUNGEN_SUBSECTION_TITLES = (
    "basis-anforderungen",
    "standard-anforderungen",
    "anforderungen bei erhöhtem schutzbedarf",
)


class GSParseError(ValueError):
    pass


GSSchichtTitle = namedtuple("GSSchichtTitle", ["reference", "name"])
GSBausteinTitle = namedtuple("GSBausteinTitle", ["reference", "name"])
GSAnforderungTitle = namedtuple(
    "GSAnforderungTitle", ["reference", "name", "gs_absicherung", "gs_verantwortliche"]
)


@dataclass
class GSAnforderung:
    title: GSAnforderungTitle
    text: Iterable[str]

    @property
    def omitted(self) -> bool:
        return cast(str, self.title.name).lower() == "entfallen"


@dataclass
class GSBaustein:
    title: GSBausteinTitle
    gs_anforderungen: Iterable[GSAnforderung]


@dataclass
class GSSchicht:
    title: GSSchichtTitle
    gs_bausteine: Iterable[GSBaustein]


@dataclass
class GSKompendium:
    title: str
    gs_schichten: Iterable[GSSchicht]


def parse_gs_schicht_title(title: str) -> GSSchichtTitle:
    match = GS_SCHICHT_TITLE_RE.match(title)
    if not match:
        raise GSParseError(f"Invalid GS-Schicht title: {title}")
    else:
        return GSSchichtTitle(match.group(1), match.group(2))


def parse_gs_baustein_title(title: str) -> GSBausteinTitle:
    match = GS_BAUSTEIN_TITLE_RE.match(title)
    if not match:
        raise GSParseError(f"Invalid GS-Baustein title: {title}")
    else:
        return GSBausteinTitle(match.group(1), match.group(3))


def parse_gs_anforderung_title(title: str) -> GSAnforderungTitle:
    match_1 = GS_ANFORDERUNG_TITLE_RE_1.match(title)
    if match_1:
        return GSAnforderungTitle(
            match_1.group(1),
            match_1.group(3),
            match_1.group(6),
            match_1.group(5),
        )
    else:
        match_2 = GS_ANFORDERUNG_TITLE_RE_2.match(title)
        if match_2:
            return GSAnforderungTitle(
                match_2.group(1),
                match_2.group(3),
                match_2.group(4),
                match_2.group(6),
            )
        else:
            raise GSParseError(f"Invalid GS-Anforderung title: {title}")
