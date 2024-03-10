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

import os
import pathlib
import ssl
from functools import lru_cache
from typing import Annotated, Any

import yaml
from pydantic import BaseModel, StringConstraints, model_validator
from uvicorn.config import LOGGING_CONFIG, SSL_PROTOCOL_VERSION

from .utils.crypto import derive_key


class DatabaseConfig(BaseModel):
    url: str = "sqlite://"
    echo: bool = False


class JiraConfig(BaseModel):
    url: str
    verify_ssl: bool | str = True


class LdapAttributeConfig(BaseModel):
    login: str
    firstname: str | None = None
    lastname: str | None = None
    email: str | None = None


class LdapConfig(BaseModel):
    protocol: Annotated[str, StringConstraints(pattern="^ldap$|^ldaps$")] = "ldap"
    host: str
    port: int | None = (
        None  # If set to None, the port is automatically set to 389 (LDAP) or 636 (LDAPS)
    )
    verify_ssl: bool | str = True
    account_dn: str | None = None
    account_password: str | None = None
    base_dn: str
    user_filter: str | None = None
    attributes: LdapAttributeConfig
    attributes_encoding: str = "utf-8"

    @model_validator(mode="after")
    def set_port_automatically(self) -> Any:
        if self.port is None:
            self.port = 636 if self.protocol == "ldaps" else 389
        return self

    @model_validator(mode="after")
    def account_password_must_be_set(self) -> Any:
        if self.account_dn and not self.account_password:
            raise ValueError("account_password must be set when account_dn is set")
        return self


class FastApiConfig(BaseModel):
    docs_url: str | None = None  # "/docs"
    redoc_url: str | None = None  # "/redoc"


class UvicornConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: str = "error"
    log_filename: str | None = None
    ssl_keyfile: str | None = None
    ssl_certfile: str | None = None
    ssl_keyfile_password: str | None = None
    ssl_version: int = SSL_PROTOCOL_VERSION
    ssl_cert_reqs: int = ssl.CERT_NONE
    ssl_ca_certs: str | None = None
    ssl_ciphers: str = "TLSv1"

    @property
    def log_config(self) -> dict:
        if not self.log_filename:
            return LOGGING_CONFIG

        custom_logging_config = LOGGING_CONFIG.copy()
        custom_logging_config["formatters"]["default"]["use_colors"] = False
        custom_logging_config["formatters"]["access"]["use_colors"] = False
        custom_logging_config["handlers"] = {
            "default": {
                "class": "logging.FileHandler",
                "formatter": "default",
                "filename": self.log_filename,
                "mode": "a",
                "encoding": "utf-8",
            },
            "access": {
                "class": "logging.FileHandler",
                "formatter": "access",
                "filename": self.log_filename,
                "mode": "a",
                "encoding": "utf-8",
            },
        }
        return custom_logging_config


class AuthConfig(BaseModel):
    secret: str | bytes = os.urandom(32)

    @property
    def derived_key(self) -> bytes:
        return derive_key(self.secret)


class Config(BaseModel):
    database: DatabaseConfig
    jira: JiraConfig | None = None
    ldap: LdapConfig | None = None
    fastapi: FastApiConfig = FastApiConfig()
    uvicorn: UvicornConfig = UvicornConfig()
    auth: AuthConfig = AuthConfig()

    @model_validator(mode="before")
    @classmethod
    def at_least_one_service(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("jira") and not data.get("ldap"):
            raise ValueError("At least one of jira or ldap must be set")
        return data


CONFIG_FILENAME = "config.yml"


def _to_abs_filename(filename: str) -> str:
    return pathlib.Path(__file__).parent.joinpath("..", filename).resolve()


@lru_cache()
def load_config() -> Config:
    with open(_to_abs_filename(CONFIG_FILENAME), "r") as config_file:
        config_data = yaml.safe_load(config_file)
    return Config.model_validate(config_data)
