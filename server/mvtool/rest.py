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

import tornado.web


class RestHandler(tornado.web.RequestHandler):
    def initialize(self, object_schema):
        self._object_schema = object_schema
        self._objects = dict()

    def create_object(self):
        pass

    def get_object(self, id_):
        pass

    def update_object(self, id_):
        pass

    def delete_object(self, id_):
        pass

    def get_objects(self):
        pass

    def post(self):
        pass

    def get(self, id_):
        self.write(f"Hello, {id_}")

    def put(self, id_):
        pass

    def delete(self, id_):
        pass