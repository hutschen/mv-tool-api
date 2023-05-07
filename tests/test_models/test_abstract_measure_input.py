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

from mvtool.models.measures import AbstractMeasureInput


@pytest.mark.parametrize(
    "completion_status, completion_comment",
    [
        # Test case when both fields are set
        ("completed", "Measure completed successfully"),
        # Test case when main_field is set, and dependent_field is not set
        ("completed", None),
        # Test case when both fields are not set
        (None, None),
    ],
)
def test_completion_comment_validator_no_exception(
    completion_status, completion_comment
):
    valid_input = AbstractMeasureInput(
        summary="Test summary",
        completion_status=completion_status,
        completion_comment=completion_comment,
    )
    assert valid_input.completion_status == completion_status
    assert valid_input.completion_comment == completion_comment


def test_completion_comment_validator_exception():
    # Test case when main_field is not set, and dependent_field is set
    with pytest.raises(ValueError) as exc_info:
        AbstractMeasureInput(
            summary="Test summary",
            completion_status=None,
            completion_comment="Measure completed successfully",
        )

    assert "completion_comment cannot be set when completion_status is not set" in str(
        exc_info.value
    )


@pytest.mark.parametrize(
    "verification_method, verification_status, verification_comment",
    [
        # Test case when all fields are set
        ("I", "verified", "Verification comment"),
        # Test case when verification_method is set and dependent fields are not set
        ("I", None, None),
        # Test case when verification_method is and only verification_status is set
        ("I", "verified", None),
        # Test case when verification_method is and only verification_comment is set
        ("I", None, "Verification comment"),
        # Test case when all fields are not set
        (None, None, None),
    ],
)
def test_verification_status_and_comment_validator_valid(
    verification_method, verification_status, verification_comment
):
    valid_input = AbstractMeasureInput(
        summary="Test summary",
        verification_method=verification_method,
        verification_status=verification_status,
        verification_comment=verification_comment,
    )
    assert valid_input.verification_method == verification_method
    assert valid_input.verification_status == verification_status
    assert valid_input.verification_comment == verification_comment


@pytest.mark.parametrize(
    "verification_method, verification_status, verification_comment",
    [
        # Test case when verification_method is not set, and only verification_status is set
        (None, "verified", None),
        # Test case when verification_method is not set, and only verification_comment is set
        (None, None, "Verification comment"),
        # Test case when main_field is not set, and both dependent_fields are set
        (None, "verified", "Verification comment"),
    ],
)
def test_verification_status_and_comment_validator_invalid(
    verification_method, verification_status, verification_comment
):
    with pytest.raises(ValueError) as exc_info:
        AbstractMeasureInput(
            summary="Test summary",
            verification_method=verification_method,
            verification_status=verification_status,
            verification_comment=verification_comment,
        )

    assert "when verification_method is not set" in str(exc_info.value)
