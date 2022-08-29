# coding: utf-8
#
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

import uvicorn
from mvtool.config import UvicornConfig


if __name__ == "__main__":
    # TODO: load config from file and configure uvicorn
    config = UvicornConfig()
    uvicorn.run(
        "mvtool:app",
        reload=True,
        log_level=config.log_level,
        log_config=config.logging_config,
    )
