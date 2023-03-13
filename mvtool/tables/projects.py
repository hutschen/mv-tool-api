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


from fastapi import Depends

from ..models import ProjectInput, ProjectOutput
from .common import ColumnDef, ColumnsDef
from .jira_ import JiraProjectImport, get_jira_project_columns_def


class ProjectImport(ProjectInput):
    id: int | None = None
    jira_project: JiraProjectImport | None = None


class ProjectExport(ProjectOutput):
    pass


def get_project_columns_def(
    jira_project_columns_def: ColumnsDef = Depends(get_jira_project_columns_def),
) -> ColumnsDef[ProjectImport, ProjectExport]:
    jira_project_columns_def.attr_name = "jira_project"

    return ColumnsDef(
        ProjectImport,
        "Project",
        [
            ColumnDef("ID", "id"),
            ColumnDef("Name", "name", required=True),
            ColumnDef("Description", "description"),
            jira_project_columns_def,
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
