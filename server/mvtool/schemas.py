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

from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from . import models


class RequirementSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = models.Requirement
        load_instance = True
        transient = True

    id = auto_field()
    summary = auto_field()
    description = auto_field()