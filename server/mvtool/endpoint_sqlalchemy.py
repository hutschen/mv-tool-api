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
from .endpoint import EndpointHandler

class SQLAlchemyEndpointHandler(EndpointHandler):
    def initialize(self, sqlalchemy_session, **kwargs):
        super().initialize(**kwargs)
        self._sqlalchemy_session = sqlalchemy_session

    async def list_objects(self, **kwargs):
        return await super().list_objects(**kwargs)

    async def get_object(self, id_):
        return await super().get_object(**kwargs)

    async def create_object(self, object_, **kwargs):
        async with self._sqlalchemy_session() as session:
            async with session.begin():
                session.add(object_)
        return object_

    async def update_object(self, object_, **kwargs):
        return await super().update_object(object_, **kwargs)

    async def delete_object(self, **kwargs):
        return await super().delete_object(**kwargs)
