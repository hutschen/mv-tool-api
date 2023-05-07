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

import pytest

from mvtool.models.common import AbstractComplianceInput


@pytest.mark.parametrize(
    "dependent_value, main_value, expected_value",
    [
        # Test case when both fields are set
        ("dependent_value", "main_value", "dependent_value"),
        # Test case when main_field is set, and dependent_field is not set
        (None, "main_value", None),
        # Test case when both fields are not set
        (None, None, None),
    ],
)
def test_dependent_field_validator_valid(dependent_value, main_value, expected_value):
    result = AbstractComplianceInput._dependent_field_validator(
        "dependent_field", "main_field", dependent_value, {"main_field": main_value}
    )
    assert result == expected_value


def test_dependent_field_validator_invalid():
    # Test case when main_field is not set, and dependent_field is set
    with pytest.raises(ValueError) as exc_info:
        AbstractComplianceInput._dependent_field_validator(
            "dependent_field", "main_field", "dependent_value", {"main_field": None}
        )
    assert (
        str(exc_info.value)
        == "dependent_field cannot be set when main_field is not set"
    )


@pytest.mark.parametrize(
    "compliance_status, compliance_comment",
    [
        # Test case when both fields are set
        ("C", "Test comment"),
        # Test case when main_field is set, and dependent_field is not set
        ("C", None),
        # Test case when both fields are not set
        (None, None),
    ],
)
def test_compliance_comment_validator_valid(compliance_status, compliance_comment):
    valid_input = AbstractComplianceInput(
        compliance_status=compliance_status, compliance_comment=compliance_comment
    )
    assert valid_input.compliance_status == compliance_status
    assert valid_input.compliance_comment == compliance_comment


def test_compliance_comment_validator_invalid():
    # Test case when main_field is not set, and dependent_field is set
    with pytest.raises(ValueError) as exc_info:
        AbstractComplianceInput(
            compliance_status=None, compliance_comment="Test comment"
        )

    assert "compliance_comment cannot be set when compliance_status is not set" in str(
        exc_info.value
    )
