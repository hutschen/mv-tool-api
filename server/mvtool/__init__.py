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
from tempfile import TemporaryDirectory
import sqlalchemy
import tornado.web
import tornado.ioloop
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from .utils.endpoint import EndpointHandler
from .utils.openapi import prepare_swagger_ui_dir
from .models import Base
from . import endpoints
from .openapi_spec import openapi_spec


class App(object):
    def __init__(self):
        self._config = dict(tornado=dict(debug=True, port=8888))
        
        # connect to database
        self._sqlalchemy_engine = create_async_engine(
            'sqlite+aiosqlite:///:memory:', echo=True)
        self._sqlalchemy_sessionmaker = sessionmaker(
            self._sqlalchemy_engine, expire_on_commit=False, class_=AsyncSession)

    async def initialize_database(self):
        async with self._sqlalchemy_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    def serve(self):
        self._swagger_ui_tempdir = TemporaryDirectory()
        prepare_swagger_ui_dir(self._swagger_ui_tempdir.name, openapi_spec)

        tornado_config = self._config['tornado']
        tornado_app = tornado.web.Application([
            (r'/jira-instances/', EndpointHandler, dict(
                endpoint_class=endpoints.JiraInstancesEndpoint,
                sqlalchemy_sessionmaker=self._sqlalchemy_sessionmaker
            )),
            (r'/jira-instances/(?P<id>[0-9]+)', EndpointHandler, dict(
                endpoint_class=endpoints.JiraInstancesEndpoint,
                sqlalchemy_sessionmaker=self._sqlalchemy_sessionmaker
            )),
            (r'/requirements/', EndpointHandler, dict(
                endpoint_class=endpoints.RequirementsEndpoint,
                sqlalchemy_sessionmaker=self._sqlalchemy_sessionmaker
            )),
            (r'/requirements/(?P<id>[0-9]+)', EndpointHandler, dict(
                endpoint_class=endpoints.RequirementsEndpoint,
                sqlalchemy_sessionmaker=self._sqlalchemy_sessionmaker
            )),
            (r'/api/(.*)', tornado.web.StaticFileHandler, dict(
               path=self._swagger_ui_tempdir.name,
               default_filename='index.html' 
            )),
        ], debug=tornado_config['debug'])
        tornado_app.listen(tornado_config['port'])

        signal_handler = \
            lambda signal, frame: tornado.ioloop.IOLoop.current(
                ).add_callback_from_signal(self.stop_serving)
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        tornado.ioloop.IOLoop.current().run_sync(self.initialize_database)
        tornado.ioloop.IOLoop.current().start()

    def stop_serving(self):
        tornado.ioloop.IOLoop.current().stop()
        self._swagger_ui_tempdir.cleanup()