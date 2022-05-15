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

from pyparsing import StringEnd
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    password_hash = Column(String)
    jira_api_token = Column(String)


class JiraIssue(Base):
    __tablename__ = 'jira_issues'
    id = Column(Integer, primary_key=True)


class JiraProject(Base):
    __tablename__ = 'jira_projects'
    id = Column(Integer, primary_key=True)


class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True)


class Measure(Base):
    __tablename__ = 'measures'
    id = Column(Integer, primary_key=True)
    summary = Column(String)
    documents = None
    ticket = None


class Requirement(Base):
    __tablename__ = 'requirements'
    id = Column(Integer, primary_key=True)
    reference = Column(String)
    summary = Column(String)
    description = Column(String)
    target = Column(String)
    compliance = Column(String)
    statement_of_compliance = Column(String)
    measures = None


class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    requirements = True