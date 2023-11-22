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

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import migration, tables
from .angular import AngularFiles
from .auth import jira_ as auth_jira
from .config import load_config
from .db import database
from .handlers import (
    catalog_modules,
    catalog_requirements,
    catalogs,
    documents,
    jira_,
    measures,
    projects,
    requirements,
)

config = load_config()


def get_app(lifespan=None) -> FastAPI:
    app = FastAPI(
        title="MV-Tool",
        docs_url=config.fastapi.docs_url,
        redoc_url=config.fastapi.redoc_url,
        lifespan=lifespan,
    )
    app.include_router(auth_jira.router)
    app.include_router(jira_.router, prefix="/api")
    app.include_router(catalogs.router, prefix="/api")
    app.include_router(catalog_modules.router, prefix="/api")
    app.include_router(catalog_requirements.router, prefix="/api")
    app.include_router(projects.router, prefix="/api")
    app.include_router(tables.router, prefix="/api")
    app.include_router(requirements.router, prefix="/api")
    app.include_router(measures.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.mount("/", AngularFiles(directory="htdocs", html=True))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://localhost:4200"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup logic
    migration.migrate(config.database)
    database.setup_connection(config.database)
    yield
    # Shutdown logic
    database.dispose_connection()


app = get_app(lifespan)


def serve():
    uvicorn.run(
        "mvtool:app",
        host=config.uvicorn.host,
        port=config.uvicorn.port,
        reload=config.uvicorn.reload,
        log_level=config.uvicorn.log_level,
        log_config=config.uvicorn.log_config,
        ssl_keyfile=config.uvicorn.ssl_keyfile,
        ssl_certfile=config.uvicorn.ssl_certfile,
        ssl_keyfile_password=config.uvicorn.ssl_keyfile_password,
        ssl_version=config.uvicorn.ssl_version,
        ssl_cert_reqs=config.uvicorn.ssl_cert_reqs,
        ssl_ca_certs=config.uvicorn.ssl_ca_certs,
        ssl_ciphers=config.uvicorn.ssl_ciphers,
    )
