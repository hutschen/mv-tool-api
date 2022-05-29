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

from os import urandom
import yaml
from marshmallow import Schema, fields, missing, post_load
from .utils.auth import JiraCredentialsSchema


class ConfigMorsel(object):
    def __init__(self, config_data):
        self.config_data = config_data

    def __getattribute__(self, name):
        try:
            return super().__getattribute__('config_data')[name]
        except KeyError:
            return super().__getattribute__(name)


class ConfigMorselSchema(Schema):
    @post_load
    def make_config_morsel(self, config_data, **kwargs):
        return ConfigMorsel(config_data)


class TornadoConfigSchema(ConfigMorselSchema):
    port = fields.Integer(missing=8888)
    debug = fields.Boolean(missing=False)
    cookie_secret = fields.String(missing=urandom(32))


class SQLAlchemyConfigSchema(ConfigMorselSchema):
    url = fields.String(missing='sqlite+aiosqlite:///:memory:')
    echo = fields.Boolean(missing=False)


class TestingConfigSchema(ConfigMorselSchema):
    jira_credentials = fields.Nested(JiraCredentialsSchema, missing=None)


class ConfigSchema(ConfigMorselSchema):
    tornado = fields.Nested(
        TornadoConfigSchema, missing=TornadoConfigSchema().load(dict()))
    sqlalchemy = fields.Nested(
        SQLAlchemyConfigSchema, missing=SQLAlchemyConfigSchema().load(dict()))
    testing = fields.Nested(
        TestingConfigSchema, missing=TestingConfigSchema().load(dict()))


def load_config(config_filename=None):
    if config_filename:
        with open(config_filename, 'r') as config_file:
            config_data = yaml.safe_load(config_file)
    else:
        config_data = dict()
    return ConfigSchema().load(config_data)