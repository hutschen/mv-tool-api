# coding: utf-8
#
# Copyright (C) 2022 Helmar Hutschenreuter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from mvtool.views import excel
from .views import jira_, projects, requirements, measures, documents
from . import database, config

app = FastAPI(title="MV-Tool")
app.include_router(jira_.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(requirements.router, prefix="/api")
app.include_router(measures.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(excel.router, prefix="/api")
app.mount("/", StaticFiles(directory="htdocs", html=True))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    config_ = config.load_config()
    database.setup_engine(config_)
    database.create_all()


@app.on_event("shutdown")
def on_shutdown():
    database.dispose_engine()
