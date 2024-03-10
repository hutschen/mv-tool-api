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

# Using a Debian-based lightweight base image
FROM python:3.11-slim

# Set working directory
WORKDIR /workspace

# Install dependencies including gcc, libldap2-dev, libsasl2-dev to build python-ldap
COPY ./Pipfile ./Pipfile.lock ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       make \
       git \
       zsh \
       curl \
       gcc \
       libldap2-dev \
       libsasl2-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --upgrade pip \
    && pip3 install pipenv \
    && pipenv install --ignore-pipfile --dev

# Install Oh-My-Zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
