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

from tornado.web import HTTPError


class BadRequest(HTTPError):
    def __init__(self, *args, **kwargs):
        super().__init__(400, *args, **kwargs)


class Unauthorized(HTTPError):
    def __init__(self, *args, **kwargs):
        super().__init__(401, *args, **kwargs)


class Forbidden(HTTPError):
    def __init__(self, *args, **kwargs):
        super().__init__(403, *args, **kwargs)


class NotFound(HTTPError):
    def __init__(self, *args, **kwargs):
        super().__init__(404, *args, **kwargs)


class MethodNotAllowed(HTTPError):
    def __init__(self, *args, **kwargs):
        super().__init__(405, *args, **kwargs)