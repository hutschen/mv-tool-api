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

import yaml
import pathlib
from fastapi import Depends
from pydantic import BaseModel, AnyHttpUrl


class Config(BaseModel):
    jira_server_url: AnyHttpUrl
    username: str | None = None
    password: str | None = None


def get_config_filename():
    return pathlib.Path.joinpath(
        pathlib.Path(__file__).parent, '../config.yml').resolve()


def load_config(config_filename = Depends(get_config_filename)):
    if config_filename:
        with open(config_filename, 'r') as config_file:
            config_data = yaml.safe_load(config_file)
    else:
        config_data = dict()
    return Config.parse_obj(config_data)