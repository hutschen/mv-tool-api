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
import tornado.web
import tornado.ioloop
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from marshmallow import Schema, fields
from .endpoint_sqlalchemy import SQLAlchemyEndpointHandler

class RequirementSchema(Schema):
    id_ = fields.Int(data_key='id', missing=None)
    name = fields.Str()
    description = fields.Str()


class RequirementsHandler(SQLAlchemyEndpointHandler):
    def get_object(self, id_):
        return dict(
            id_=id_, name='Requirement', description='A short description')


class App(object):
    def __init__(self):
        self._config = dict(tornado=dict(debug=True, port=8888))
        
        # connect to database
        sqlalchemy_engine = create_async_engine(
            'sqlite+aiosqlite:///:memory:', echo=True)
        self._sqlalchemy_session = sessionmaker(
            sqlalchemy_engine, expire_on_commit=False, class_=AsyncSession)

    def serve(self):
        tornado_config = self._config['tornado']
        tornado_app = tornado.web.Application([
            (r"/", RequirementsHandler, 
                dict(sqlalchemy_session=self._sqlalchemy_session, object_schema=RequirementSchema)),
            (r"/(?P<id>[0-9]+)", RequirementsHandler, 
                dict(sqlalchemy_session=self._sqlalchemy_session, object_schema=RequirementSchema)),
        ], debug=tornado_config['debug'])
        tornado_app.listen(tornado_config['port'])

        signal_handler = \
            lambda signal, frame: tornado.ioloop.IOLoop.current(
                ).add_callback_from_signal(self.stop_serving)
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        tornado.ioloop.IOLoop.current().start()

    def stop_serving(self):
        tornado.ioloop.IOLoop.current().stop()