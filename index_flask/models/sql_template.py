#!/usr/bin/env python
# coding=utf-8
# Stan 2017-07-11

from __future__ import (division, absolute_import,
                        print_function, unicode_literals)

import uuid
from datetime import datetime

from ..app import db
from . import StrType


class SQLTemplate(db.Model):
    __tablename__ = 'sql_templates'
    __rev__ = '2018-09-29'

    user = db.relationship('User', backref=db.backref(__tablename__,
        cascade='all, delete, delete-orphan'))
    group = db.relationship('Group', backref=db.backref(__tablename__,
        cascade='all, delete, delete-orphan'))

    id = db.Column(db.Integer, primary_key=True)
    _user_id = db.Column(db.Integer, db.ForeignKey('users.id',
        onupdate="CASCADE", ondelete="CASCADE"))
    _group_id = db.Column(db.Integer, db.ForeignKey('groups.id',
        onupdate="CASCADE", ondelete="CASCADE"))

    name = db.Column(db.String, nullable=False, default='')
    uid = db.Column(StrType, nullable=False, default=uuid.uuid4)
    deleted = db.Column(db.Boolean, nullable=False, default=False)

    value = db.Column(db.Text, nullable=False, default='')
    description = db.Column(db.Text, nullable=False, default='')
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    db.Index('sql_template_', _user_id, _group_id, name, unique=True)

    def __repr__(self):
        return '<SQLTemplate {0!r}>'.format(self.name)

    def get_id(self):
        return self.uid