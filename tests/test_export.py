# coding: utf-8
# 
# Copyright 2022 Helmar Hutschenreuter
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation. You may obtain
# a copy of the GNU AGPL V3 at https://www.gnu.org/licenses/.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU AGPL V3 for more details.

from fastapi.responses import FileResponse

from mvtool.models import Measure, Project
from mvtool.views.export import ExportMeasuresView

def test_download_measures_excel(
        export_measures_view: ExportMeasuresView, excel_temp_file, 
        create_project: Project, create_measure: Measure):
    result = export_measures_view.download_measures_excel(
        create_project.id, temp_file=excel_temp_file)
    assert isinstance(result, FileResponse)
    assert result.media_type == \
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'