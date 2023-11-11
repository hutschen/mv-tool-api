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

from unittest.mock import Mock

import pytest

from mvtool.db.schema import CatalogModule, CatalogRequirement
from mvtool.gsparser.common import (
    GSAnforderung,
    GSAnforderungTitle,
    GSBaustein,
    GSBausteinTitle,
    GSParseError,
)
from mvtool.handlers.gs import (
    get_catalog_module_from_gs_baustein,
    get_gs_baustein_from_uploaded_word_file,
)
from mvtool.utils.errors import ValueHttpError


def test_get_gs_baustein_from_uploaded_word_file_fails(monkeypatch):
    # Creates a mock object that throws a GSParseError when called
    mock_parse_function = Mock(side_effect=GSParseError("Test error"))
    mock_temp_file = Mock()

    # Replace the parse_gs_baustein_word_file function with the mock object
    monkeypatch.setattr(
        "mvtool.handlers.gs.parse_gs_baustein_word_file",
        mock_parse_function,
    )

    with pytest.raises(ValueHttpError, match="Test error"):
        # next() is used to get the return value of the generator
        next(get_gs_baustein_from_uploaded_word_file(mock_temp_file))


def test_get_gs_baustein_from_uploaded_word_file_success(monkeypatch):
    # Creates a mock object that returns a catalog module when called
    mock_parse_function = Mock()
    mock_parse_function.return_value = object()
    mock_temp_file = Mock()

    # Replace the parse_gs_baustein_word_file function with the mock object
    monkeypatch.setattr(
        "mvtool.handlers.gs.parse_gs_baustein_word_file",
        mock_parse_function,
    )

    # Call the function and check if the mock object is returned
    result = next(get_gs_baustein_from_uploaded_word_file(mock_temp_file))
    assert result == mock_parse_function.return_value


@pytest.mark.parametrize("skip_omitted", [True, False])
def test_get_catalog_module_from_gs_baustein(skip_omitted):
    # Create a GS Baustein
    gs_baustein = GSBaustein(
        title=GSBausteinTitle("ABC.1", "Sample Name"),
        gs_anforderungen=[
            GSAnforderung(
                title=GSAnforderungTitle("ABC.1.A1", "Sample Name", "B", "Role"),
                text=["Sample", "text"],
            ),
            GSAnforderung(
                title=GSAnforderungTitle("ABC.1.A1", "Entfallen", "B", "Role"),
                text=["Sample", "text"],
            ),
        ],
    )

    # Convert the GS Baustein to a catalog module
    catalog_module = get_catalog_module_from_gs_baustein(gs_baustein, skip_omitted)

    # Check if the catalog module is created correctly
    assert isinstance(catalog_module, CatalogModule)
    assert catalog_module.reference == "ABC.1"
    assert catalog_module.title == "Sample Name"

    # Define the expected requirement summaries based on skip_omitted parameter
    expected_summaries = (
        ["Sample Name"] if skip_omitted else ["Sample Name", "Entfallen"]
    )

    # Assert that the catalog requirements match the expected results
    for i, summary in enumerate(expected_summaries):
        catalog_requirement: CatalogRequirement = catalog_module.catalog_requirements[i]
        assert catalog_requirement.reference == f"ABC.1.A1"
        assert catalog_requirement.summary == summary
        assert catalog_requirement.gs_absicherung == "B"
        assert catalog_requirement.gs_verantwortliche == "Role"
        assert catalog_requirement.description == "Sample\n\ntext"
