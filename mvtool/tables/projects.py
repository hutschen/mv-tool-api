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


from ..models import JiraProject, ProjectInput, ProjectOutput
from .common import ColumnDef, ColumnsDef


class ProjectImport(ProjectInput):
    id: int | None = None
    jira_project: JiraProject | None = None


class ProjectExport(ProjectOutput):
    pass


def get_project_columns_def() -> ColumnsDef[ProjectImport, ProjectExport]:
    return ColumnsDef(
        ProjectImport,
        "Project",
        [
            ColumnDef("ID", "id"),
            ColumnDef("Name", "name", required=True),
            ColumnDef("Description", "description"),
            ColumnsDef[JiraProject, JiraProject](
                JiraProject,
                "Jira Project",
                [
                    ColumnDef("Key", "key", required=True),
                    ColumnDef("Name", "name", ColumnDef.EXPORT_ONLY),
                    ColumnDef("Link", "url", ColumnDef.EXPORT_ONLY),
                ],
            ),
            ColumnDef(
                "Completion Progress",
                "completion_progress",
                ColumnDef.EXPORT_ONLY,
            ),
            ColumnDef(
                "Verification Progress",
                "verification_progress",
                ColumnDef.EXPORT_ONLY,
            ),
        ],
    )
