# Copyright (C) 2022 Helmar Hutschenreuter
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


def combine_flags(flags_head: bool | None, *flags_tail: bool | None) -> bool | None:
    """Combine the given boolean flags and return the result.

    Args:
        flags_head (bool or None): The first boolean flag.
        flags_tail (tuple of bools or Nones): The remaining boolean flags.

    Returns:
        bool or None: The result of combining the boolean flags with an OR operator.
        If all the input flags are None, the function returns None.
    """
    boolean_flags = [f for f in [flags_head, *flags_tail] if f is not None]
    return any(boolean_flags) if boolean_flags else None
