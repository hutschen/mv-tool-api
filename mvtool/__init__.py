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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
from .views import jira_, projects, requirements, measures, documents
from . import database, config

app = FastAPI(title='MV-Tool')
app.include_router(jira_.router, prefix='/api/jira')
app.include_router(projects.router, prefix='/api')
app.include_router(requirements.router, prefix='/api')
app.include_router(measures.router, prefix='/api')
app.include_router(documents.router, prefix='/api')
# app.include_router(tasks.router, prefix='/api')
app.mount('/', StaticFiles(directory='htdocs', html=True))
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:8000', 'http://localhost:4200'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

logging.root = logging.getLogger('gunicorn.error')

@app.on_event('startup')
def on_startup():
    config_ = config.load_config()
    database.setup_engine(config_)
    database.create_all()

@app.on_event('shutdown')
def on_shutdown():
    database.dispose_engine()