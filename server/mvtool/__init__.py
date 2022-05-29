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

import signal
from os import urandom
from tempfile import TemporaryDirectory
import tornado.web
import tornado.ioloop
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from .utils.endpoint import EndpointHandler
from .utils.openapi import prepare_swagger_ui_dir
from .config import load_config
from .models import Base
from . import endpoints
from .openapi_spec import openapi_spec


class SQLAlchemyDatabase(object):
    def __init__(self, *args, **kwargs):
        self.engine = create_async_engine(*args, **kwargs)
        self.sessionmaker = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession)

    async def reset(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)


class App(object):
    def __init__(self, config_filename=None):
        self.config = load_config(config_filename)
        self.database = SQLAlchemyDatabase(
            self.config.sqlalchemy.url, echo=self.config.sqlalchemy.echo)

        self._swagger_ui_tempdir = TemporaryDirectory()
        prepare_swagger_ui_dir(self._swagger_ui_tempdir.name, openapi_spec)

        self.tornado_app = tornado.web.Application([
            (r'/jira-user/', EndpointHandler, dict(
                endpoint_class=endpoints.JiraUserEndpoint,
                sqlalchemy_sessionmaker=self.database.sessionmaker
            )),
            (r'/jira-instances/', EndpointHandler, dict(
                endpoint_class=endpoints.JiraInstancesEndpoint,
                sqlalchemy_sessionmaker=self.database.sessionmaker
            )),
            (r'/jira-instances/(?P<id>[0-9]+)', EndpointHandler, dict(
                endpoint_class=endpoints.JiraInstancesEndpoint,
                sqlalchemy_sessionmaker=self.database.sessionmaker
            )),
            (r'/jira-user/jira-projects/', EndpointHandler, dict(
                endpoint_class=endpoints.JiraProjectsEndpoint,
                sqlalchemy_sessionmaker=self.database.sessionmaker
            )),
            (r'/jira-user/jira-projects/(?P<id>[0-9]+)', EndpointHandler, dict(
                endpoint_class=endpoints.JiraProjectsEndpoint,
                sqlalchemy_sessionmaker=self.database.sessionmaker
            )),
            (r'/jira-user/projects/', EndpointHandler, dict(
                endpoint_class=endpoints.ProjectsEndpoint,
                sqlalchemy_sessionmaker=self.database.sessionmaker
            )),
            (r'/jira-user/projects/(?P<id>[0-9]+)', EndpointHandler, dict(
                endpoint_class=endpoints.ProjectsEndpoint,
                sqlalchemy_sessionmaker=self.database.sessionmaker
            )),
            (r'/jira-user/requirements/', EndpointHandler, dict(
                endpoint_class=endpoints.RequirementsEndpoint,
                sqlalchemy_sessionmaker=self.database.sessionmaker
            )),
            (r'/jira-user/requirements/(?P<id>[0-9]+)', EndpointHandler, dict(
                endpoint_class=endpoints.RequirementsEndpoint,
                sqlalchemy_sessionmaker=self.database.sessionmaker
            )),
            (r'/jira-user/measures/', EndpointHandler, dict(
                endpoint_class=endpoints.MeasuresEndpoint,
                sqlalchemy_sessionmaker=self.database.sessionmaker
            )),
            (r'/jira-user/measures/(?P<id>[0-9]+)', EndpointHandler, dict(
                endpoint_class=endpoints.MeasuresEndpoint,
                sqlalchemy_sessionmaker=self.database.sessionmaker
            )),
            (r'/api/(.*)', tornado.web.StaticFileHandler, dict(
               path=self._swagger_ui_tempdir.name,
               default_filename='index.html' 
            )),
        ], 
            cookie_secret=(
                bytes(self.config.tornado.cookie_secret, 'utf-8') if 
                self.config.tornado.cookie_secret else urandom(32)
            ),
            debug=self.config.tornado.debug
        )

    def serve(self):
        self.tornado_app.listen(self.config.tornado.port)

        signal_handler = \
            lambda signal, frame: tornado.ioloop.IOLoop.current(
                ).add_callback_from_signal(self.stop_serving)
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        tornado.ioloop.IOLoop.current().run_sync(self.database.reset)
        tornado.ioloop.IOLoop.current().start()

    def stop_serving(self):
        tornado.ioloop.IOLoop.current().stop()
        self._swagger_ui_tempdir.cleanup()