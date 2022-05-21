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

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True)
    reference = Column(String)
    title = Column(String)
    description = Column(String)


class JiraInstance(Base):
    __tablename__ = 'jira_instances'
    id = Column(Integer, primary_key=True)
    url = Column(String) # jira server url


class JiraProject(Base):
    __tablename__ = 'jira_projects'
    id = Column(Integer, primary_key=True)
    key = Column(String)
    jira_instance_id = Column(Integer, ForeignKey('jira_instances.id'))
    jira_instance = relationship(
        'JiraInstance', 
        backref=backref('jira_projects', cascade='all, delete, delete-orphan'))


class JiraIssue(Base):
    __tablename__ = 'jira_issues'
    id = Column(Integer, primary_key=True)
    key = Column(String)
    summary = Column(String)
    description = Column(String)
    jira_project_id = Column(Integer, ForeignKey('jira_projects.id'))
    jira_project = relationship(
        'JiraProject', 
        backref=backref('jira_issues', cascade='all, delete, delete-orphan'))


class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    summary = Column(String)
    description = Column(String)
    completed = Column(Boolean) # will be manually changed when review is passed
    jira_issue_id = Column(Integer, ForeignKey('jira_issues.id'))
    jira_issue = relationship('JiraIssue', backref=backref('tasks'))
    measure_id = Column(Integer, ForeignKey('measures.id'))
    measure = relationship(
        'Measure', 
        backref=backref('tasks', cascade='all, delete, delete-orphan'))
    document_id = Column(Integer, ForeignKey('documents.id'))
    document = relationship('Document', backref=backref('tasks'))


class Measure(Base):
    __tablename__ = 'measures'
    id = Column(Integer, primary_key=True)
    summary = Column(String)
    requirement_id = Column(Integer, ForeignKey('requirements.id'))
    requirement = relationship(
        'Requirement', 
        backref=backref('measures', cascade='all, delete, delete-orphan'))


class Requirement(Base):
    __tablename__ = 'requirements'
    id = Column(Integer, primary_key=True)
    reference = Column(String)
    summary = Column(String)
    description = Column(String)
    target = Column(String)
    compliance_status = Column(String) # C, PC, NC, NA
    compliance_comment = Column(String)
    project_id = Column(Integer, ForeignKey('projects.id'))
    project = relationship(
        'Project', 
        backref=backref('requirements', cascade='all, delete, delete-orphan'))


class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    jira_project_id = Column(Integer, ForeignKey('jira_projects.id'))
    jira_project = relationship(
        'JiraProject',
        backref=backref('project', uselist=False))