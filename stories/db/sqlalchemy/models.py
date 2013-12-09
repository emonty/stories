# Copyright 2013 Hewlett-Packard Development Company, L.P.
# Copyright 2013 Thierry Carrez <thierry@openstack.org>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
SQLAlchemy Models for storing stories
"""

import urlparse
import warnings

from oslo.config import cfg
from sqlalchemy.ext import declarative
from sqlalchemy.orm import relationship
from sqlalchemy import schema

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Unicode
from sqlalchemy import UnicodeText

from stories.openstack.common.db.sqlalchemy import models

# Turn SQLAlchemy warnings into errors
warnings.simplefilter('error')

_sql_opts = [
    cfg.StrOpt('mysql_engine',
               default='InnoDB',
               help='MySQL engine')
]

CONF = cfg.ConfigOpts()
CONF.register_opts(_sql_opts, 'database')


def table_args():
    engine_name = urlparse.urlparse(cfg.CONF.database_connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': cfg.CONF.mysql_engine,
                'mysql_charset': "utf8"}
    return None


class IdMixin(object):
    id = Column(Integer, primary_key=True)


class StoriesBase(models.TimestampMixin,
                  IdMixin,
                  models.ModelBase):

    metadata = None

    @declarative.declared_attr
    def __tablename__(cls):
        # NOTE(jkoelker) use the pluralized name of the class as the table
        return cls.__name__.lower() + 's'

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        return d


Base = declarative.declarative_base(cls=StoriesBase)

team_membership = Table(
    'team_membership', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('team_id', Integer, ForeignKey('teams.id')),
)


class User(Base):
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_user0name'),
        schema.UniqueConstraint('email', name='uniq_user0email'),
    )
    name = Column(Unicode(255))
    email = Column(String(255))
    teams = relationship("Team", secondary="team_membership")
    tasks = relationship('Task', backref='assignee')


class Team(Base):
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_team0name'),
    )
    name = Column(Unicode(255))
    users = relationship("User", secondary="team_membership")

project_groups = Table(
    'project_groups', Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id')),
    Column('keyword_id', Integer, ForeignKey('groups.id')),
)


# TODO(mordred): Do we really need name and title?
class Project(Base):
    """Represents a software project."""

    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_project0name'),
    )

    name = Column(String(50))
    description = Column(Unicode(100))
    team_id = Column(Integer, ForeignKey('teams.id'))
    team = relationship(Team, primaryjoin=team_id == Team.id)
    tasks = relationship('Task', backref='project')


class Group(Base):
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_group0name'),
    )

    name = Column(String(50))
    title = Column(Unicode(100))
    projects = relationship("Project", secondary="project_groups")


class Branch(Base):
    # TODO(mordred): order_by release date?
    _BRANCH_STATUS = ('master', 'release', 'stable', 'unsupported')
    __tablename__ = 'branches'
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_branch0name'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    status = Column(Enum(*_BRANCH_STATUS, name='branch_status'))
    release_date = Column(DateTime, nullable=True)


class Milestone(Base):
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_milestone0name'),
    )

    name = Column(String(50))
    branch_id = Column(Integer, ForeignKey('branches.id'))
    branch = relationship(Branch, primaryjoin=branch_id == Branch.id)
    released = Column(Boolean, default=False)
    undefined = Column(Boolean, default=False)
    tasks = relationship('Task', backref='milestone')


class Story(Base):
    __tablename__ = 'stories'
    _STORY_PRIORITIES = ('Undefined', 'Low', 'Medium', 'High', 'Critical')

    creator_id = Column(Integer, ForeignKey('users.id'))
    creator = relationship(User, primaryjoin=creator_id == User.id)
    title = Column(Unicode(100))
    description = Column(UnicodeText())
    is_bug = Column(Boolean, default=True)
    priority = Column(Enum(*_STORY_PRIORITIES, name='priority'))
    tasks = relationship('Task', backref='story')
    comments = relationship('Comment', backref='story')
    tags = relationship('StoryTag', backref='story')


class Task(Base):
    _TASK_STATUSES = ('Todo', 'In review', 'Landed')

    title = Column(Unicode(100), nullable=True)
    status = Column(Enum(*_TASK_STATUSES, default='Todo'))
    story_id = Column(Integer, ForeignKey('stories.id'))
    project_id = Column(Integer, ForeignKey('projects.id'))
    assignee_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    milestone_id = Column(Integer, ForeignKey('milestones.id'), nullable=True)


class Comment(Base):

    action = Column(String(150), nullable=True)
    comment_type = Column(String(20))
    content = Column(UnicodeText)

    story_id = Column(Integer, ForeignKey('stories.id'))
    author_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    author = relationship('User', primaryjoin=author_id == User.id)


class StoryTag(Base):
    __table_args__ = (
        schema.UniqueConstraint('name', name='uniq_story_tags0name'),
    )
    name = Column(String(20))
    story_id = Column(Integer, ForeignKey('stories.id'))
