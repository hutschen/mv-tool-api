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

from pydantic import BaseModel


def field_is_set(model: BaseModel, field_name: str):
    """Return True if the given field was set in the given model.

    Args:
        model (BaseModel): The model to check.
        field_name (str): The name of the field to check.

    Returns:
        bool: True if the field was set, False otherwise.
    """
    return field_name in model.__fields_set__
