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
import asyncio
import tornado.web
import tornado.ioloop
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from .endpoint_sqlalchemy import SQLAlchemyEndpointHandler

Base = declarative_base()


class Requirement(Base):
    __tablename__ = 'requirements'
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String)
    description = sa.Column(sa.String)


class RequirementSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Requirement
        load_instance = True
        transient = True

    id = auto_field()
    name = auto_field()
    description = auto_field()


class RequirementsHandler(SQLAlchemyEndpointHandler):
    pass

class App(object):
    def __init__(self):
        self._config = dict(tornado=dict(debug=True, port=8888))
        
        # connect to database
        self._sqlalchemy_engine = create_async_engine(
            'sqlite+aiosqlite:///:memory:', echo=True)
        self._sqlalchemy_session = sessionmaker(
            self._sqlalchemy_engine, expire_on_commit=False, class_=AsyncSession)

    async def initialize_database(self):
        async with self._sqlalchemy_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

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
        tornado.ioloop.IOLoop.current().run_sync(self.initialize_database)
        tornado.ioloop.IOLoop.current().start()

    def stop_serving(self):
        tornado.ioloop.IOLoop.current().stop()