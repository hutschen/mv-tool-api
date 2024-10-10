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
from typing import Generator, Iterable, cast

from mvtool.utils.iteration import cache_iterable

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
class GSTeilanforderung:
    text: str


@dataclass
class GSAnforderung:
    title: GSAnforderungTitle
    text: Iterable[str]

    def __post_init__(self):
        self.text = cache_iterable(self.text)

    @property
    def gs_teilanforderungen(self) -> Generator[GSTeilanforderung, None, None]:
        """
        Split the requirement text into sub-requirement texts and return them as
        instances of GSTeilanforderung.
        """
        for text in self.text:
            for subtext in split_gs_anforderung_text(text):
                if subtext.strip():
                    yield GSTeilanforderung(subtext)

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


def split_gs_anforderung_text(text: str) -> Generator[str, None, None]:
    """
    Takes a requirement text as input and splits it into sub-requirement texts. The
    splitting is done by identifying German modal verbs (e.g., "MUSS", "SOLL", "DARF").
    If the text contains no modal verbs, it is returned unchanged.
    """
    # Regular expression pattern to identify modal verbs and their grammatical forms
    modal_pattern = (
        r"\b(MUSS|MÜSS(?:E|EN|TE|TEN)|SOLL(?:E|EN|TE|TEN)?|DARF|DÜRF(?:E|EN|TE|TEN))\b"
    )

    # Split the text into sentences (using punctuation marks as delimiters)
    sentences = re.split(r"(?<=[.!?])\s+", text)

    current_sub_requirement = ""
    first_modal_verb_found = False

    # Go through each sentence and check for modal verbs
    for sentence in sentences:
        sentence = sentence.strip()
        if re.search(modal_pattern, sentence):
            if first_modal_verb_found:
                if current_sub_requirement:
                    yield current_sub_requirement.strip()
                # Start a new sub-requirement with the modal verb
                current_sub_requirement = sentence
            else:
                # Add additional sentence to the current sub-requirement
                current_sub_requirement += " " + sentence
                first_modal_verb_found = True
        else:
            # Add additional sentence to the current sub-requirement
            current_sub_requirement += " " + sentence

    # Yield the last accumulated requirement if it exists
    if current_sub_requirement:
        yield current_sub_requirement.strip()
