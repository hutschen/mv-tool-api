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
FROM python:3.12-slim

# Install dependencies including gcc, libldap2-dev, libsasl2-dev to build python-ldap,
# add a custom bash prompt and enable bash-completion for all users
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       make \
       git \
       bash-completion \
       gcc \
       libldap2-dev \
       libsasl2-dev \
       bash \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --upgrade pip pipenv \
    && echo 'PS1=" \W ➜ "' >> ~/.bashrc \
    && echo "if [ -f /etc/bash_completion ]; then . /etc/bash_completion; fi" >> ~/.bashrc

# Set working directory
WORKDIR /mv-tool-api

# Create Pipenv and install Python dependencies
COPY Pipfile Pipfile.lock ./
RUN pipenv install --ignore-pipfile --dev