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


import yaml
import pathlib
from pydantic import BaseModel


class DatabaseConfig(BaseModel):
    url: str = "sqlite://"
    echo: bool = False


class JiraConfig(BaseModel):
    url: str


class Config(BaseModel):
    database: DatabaseConfig
    jira: JiraConfig


def load_config():
    config_filename = pathlib.Path.joinpath(
        pathlib.Path(__file__).parent, "../config.yml"
    ).resolve()

    with open(config_filename, "r") as config_file:
        config_data = yaml.safe_load(config_file)
    return Config.parse_obj(config_data)
