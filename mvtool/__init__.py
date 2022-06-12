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

import pathlib
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .views import jira_, projects, requirements, measures, documents, tasks
from . import database

app = FastAPI(title='MV-Tool')
app.mount('/', StaticFiles(directory='htdocs', html=True))
app.include_router(jira_.router, prefix='/api/jira')
app.include_router(projects.router, prefix='/api')
app.include_router(requirements.router, prefix='/api')
app.include_router(measures.router, prefix='/api')
app.include_router(documents.router, prefix='/api')
app.include_router(tasks.router, prefix='/api')

@app.on_event('startup')
def on_startup():
    database.create_all()
    return