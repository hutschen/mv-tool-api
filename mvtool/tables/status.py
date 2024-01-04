# Copyright (C) 2024 Helmar Hutschenreuter
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

from .columns import Column


def get_completion_columns() -> tuple[Column]:
    return (
        Column("Open Count", "open_count", Column.EXPORT_ONLY),
        Column("In Progress Count", "in_progress_count", Column.EXPORT_ONLY),
        Column("Completed Count", "completed_count", Column.EXPORT_ONLY),
        Column("Completion Progress", "completion_progress", Column.EXPORT_ONLY),
    )


def get_verification_columns() -> tuple[Column]:
    return (
        Column("Verification Progress", "verification_progress", Column.EXPORT_ONLY),
    )


def get_status_columns() -> tuple[Column]:
    return (
        *get_completion_columns(),
        *get_verification_columns(),
    )
