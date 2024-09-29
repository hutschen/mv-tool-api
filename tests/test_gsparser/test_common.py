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

import pytest

from mvtool.gsparser.common import (
    GSAnforderungTitle,
    GSBausteinTitle,
    GSParseError,
    GSSchichtTitle,
    parse_gs_anforderung_title,
    parse_gs_baustein_title,
    parse_gs_schicht_title,
    split_gs_anforderung_text,
)


@pytest.mark.parametrize(
    "title, expected",
    [
        ("ABC Sample Name", GSSchichtTitle("ABC", "Sample Name")),
        ("   ABC Sample Name", GSSchichtTitle("ABC", "Sample Name")),
        ("ABC   Sample Name", GSSchichtTitle("ABC", "Sample Name")),
        ("ABC Sample Name   ", GSSchichtTitle("ABC", "Sample Name")),
    ],
)
def test_parse_gs_schicht_title_valid(title, expected):
    result = parse_gs_schicht_title(title)
    assert result == expected


@pytest.mark.parametrize(
    "invalid_title",
    [
        "ABC.1 Sample Name",
        "123 Sample Name",
        "AB Sample Name",
        "Sample Name",
        "ABC",
        "",
    ],
)
def test_parse_gs_schicht_title_invalid(invalid_title):
    with pytest.raises(GSParseError, match="Invalid GS-Schicht title"):
        parse_gs_schicht_title(invalid_title)


@pytest.mark.parametrize(
    "title, expected",
    [
        ("ABC.1 Sample Name", GSBausteinTitle("ABC.1", "Sample Name")),
        ("   ABC.1 Sample Name", GSBausteinTitle("ABC.1", "Sample Name")),
        ("ABC.1   Sample Name", GSBausteinTitle("ABC.1", "Sample Name")),
        ("ABC.1 Sample Name   ", GSBausteinTitle("ABC.1", "Sample Name")),
    ],
)
def test_parse_gs_baustein_title_valid(title, expected):
    result = parse_gs_baustein_title(title)
    assert result == expected


@pytest.mark.parametrize(
    "invalid_title",
    [
        "ABC Sample Name",
        "123 Sample Name",
        "AB.1 Sample Name",
        "Sample Name",
        "ABC.1",
        "",
    ],
)
def test_parse_gs_baustein_title_invalid(invalid_title):
    with pytest.raises(GSParseError, match="Invalid GS-Baustein title"):
        parse_gs_baustein_title(invalid_title)


@pytest.mark.parametrize(
    "title, expected",
    [
        # Using GS_ANFORDERUNG_TITLE_RE_1
        (
            "ABC.1.A1 Sample Name [Role] (B)",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
        ),
        (
            "ABC.1.A1 Sample Name [Role] (S)",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "S", "Role"),
        ),
        (
            "ABC.1.A1 Sample Name [Role] (H)",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "H", "Role"),
        ),
        (
            "   ABC.1.A1 Sample Name [Role] (B)",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
        ),
        (
            "ABC.1.A1   Sample Name [Role] (B)",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
        ),
        (
            "ABC.1.A1 Sample Name   [Role] (B)",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
        ),
        (
            "ABC.1.A1 Sample Name [Role]   (B)",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
        ),
        (
            "ABC.1.A1 Sample Name [Role] (B)   ",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
        ),
        (
            "ABC.1.A1 Sample Name (B)",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", None),
        ),
        # Using GS_ANFORDERUNG_TITLE_RE_2
        (
            "ABC.1.A1 Sample Name (B) [Role]",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
        ),
        (
            "ABC.1.A1 Sample Name (S) [Role]",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "S", "Role"),
        ),
        (
            "ABC.1.A1 Sample Name (H) [Role]",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "H", "Role"),
        ),
        (
            "   ABC.1.A1 Sample Name (B) [Role]",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
        ),
        (
            "ABC.1.A1   Sample Name (B) [Role]",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
        ),
        (
            "ABC.1.A1 Sample Name   (B) [Role]",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
        ),
        (
            "ABC.1.A1 Sample Name (B)   [Role]",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
        ),
        (
            "ABC.1.A1 Sample Name (B) [Role]   ",
            GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
        ),
    ],
)
def test_parse_gs_anforderung_title_valid(title, expected):
    result = parse_gs_anforderung_title(title)
    assert result == expected


@pytest.mark.parametrize(
    "invalid_title",
    [
        "ABC.1.A1 Sample Name [Role] (X)",
        "ABC.1.A1 Sample Name [Role]",
        "ABC.1.A1 Sample Name (B) []",
        "ABC.1.A1 Sample Name [] (B)",
        "ABC.1.A1 Sample Name",
        "Sample Name",
        "ABC.1.A1",
        "",
    ],
)
def test_parse_gs_anforderung_title_invalid(invalid_title):
    with pytest.raises(GSParseError, match="Invalid GS-Anforderung title"):
        parse_gs_anforderung_title(invalid_title)


@pytest.mark.parametrize(
    "expected",
    [
        # Empty string
        [""],
        # Single sentence with modal verb
        ["Die Führungskraft MUSS die Entscheidung treffen."],
        # Single sentence without modal verb
        ["Die Führungskraft trifft die Entscheidung."],
        # Sentences without modal verbs
        [
            "Die Führungskraft trifft die Entscheidung."
            + " Sie handelt dabei nach dem vorgegebenen Prozess."
        ],
        # First sentence with modal verb, second sentence without modal verb
        [
            "Die Führungskraft MUSS die Entscheidung treffen."
            + " Sie handelt dabei nach dem vorgegebenen Prozess."
        ],
        # First sentence without modal, second sentence with modal verb
        [
            "Die Führungskraft trifft die Entscheidung."
            + " Sie MUSS dabei nach dem vorgegebenen Prozess handeln."
        ],
        # First sentence without modal verb, second sentence with modal verb,
        # third sentence without modal verb
        [
            "Die Führungskraft trifft die Entscheidung."
            + " Sie MUSS dabei nach dem vorgegebenen Prozess handeln.",
            "Die Mitarbeitenden MÜSSEN die Anweisungen befolgen.",
        ],
        # First sentence with modal verb, second sentence without modal verb,
        # third sentence with modal verb
        [
            "Die Führungskraft MUSS die Entscheidung treffen."
            + " Sie handelt dabei nach dem vorgegebenen Prozess.",
            "Die Mitarbeitenden MÜSSEN die Anweisungen befolgen.",
        ],
        # Multiple sentences with multiple forms of modal verb "muss"
        [
            "Die Führungskraft MUSS die Entscheidung treffen.",
            "Die Mitarbeitenden MÜSSEN die Anweisungen befolgen.",
            "Die Entschiedung MÜSSTE im Sinne des Teams getroffen werden.",
            "Die Mitarbeitenden MÜSSTEN die Führungskraft unterstützen.",
            "Die Führungskraft MÜSSE die Mitarbeitenden unterstützen.",
        ],
        # Multiple with multiple forms of modal verb "soll"
        [
            "Die Führungskraft SOLL die Entscheidung treffen.",
            "Die Mitarbeitenden SOLLEN die Anweisungen befolgen.",
            "Die Entschiedung SOLLTE im Sinne des Teams getroffen werden.",
            "Die Mitarbeitenden SOLLTEN die Führungskraft unterstützen.",
            "Die Führungskraft SOLLE die Mitarbeitenden unterstützen.",
        ],
        # Multiple with multiple forms of modal verb "darf"
        [
            "Die Führungskraft DARF die Entscheidung treffen.",
            "Die Mitarbeitenden DÜRFEN die Anweisungen befolgen.",
            "Die Entschiedung DÜRFTE im Sinne des Teams getroffen werden.",
            "Die Mitarbeitenden DÜRFTEN die Führungskraft unterstützen.",
            "Die Führungskraft DÜRFE die Mitarbeitenden unterstützen.",
        ],
    ],
)
def test_split_requirements_by_sentences_2(expected):
    text = " ".join(expected)
    assert list(split_gs_anforderung_text(text)) == expected
