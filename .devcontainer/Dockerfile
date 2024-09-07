# Copyright (C) 2024 Helmar Hutschenreuter
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

# Using a lightweight Alpine-based base image
FROM python:3.12.5-alpine3.20

# Install general dependencies for development:
# - bash, bash-completion, make, git
#
# Install project dependencies:
# - mailcap for inferring MIME types from file extensions
# - libpq is the PostgreSQL client library
# - openldap-clients for LDAP support
# - build-deps, build-base for building Python C extensions
# - libpq-dev to build psycopg2 for PostgreSQL support
# - openldap-dev to build python-ldap for LDAP support
# - libffi-dev for building Python C extensions that require ffi
RUN apk update \
    && apk add --no-cache \
        bash \
        bash-completion \
        make \
        git \
        mailcap \
        libpq \
        openldap-clients \
        build-base \
        libpq-dev \
        openldap-dev \
        libffi-dev \
    && pip3 install --no-cache-dir --upgrade pip pipenv \
    && echo 'PS1=" \W ➜ "' >> ~/.bashrc \
    && echo "if [ -f /usr/share/bash-completion/bash_completion ]; then . /usr/share/bash-completion/bash_completion; fi" >> ~/.bashrc \
    && sed -i 's|/bin/sh|/bin/bash|' /etc/passwd

# Set working directory
WORKDIR /mv-tool-api

# Create Pipenv and install Python dependencies
COPY Pipfile Pipfile.lock ./
RUN pipenv install --ignore-pipfile --dev