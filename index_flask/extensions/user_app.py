#!/usr/bin/env python
# coding=utf-8
# Stan 2016-07-12

from __future__ import (division, absolute_import,
                        print_function, unicode_literals)

import re
import hashlib
import random
from datetime import datetime

from flask import request, render_template, jsonify, redirect, url_for, flash
from jinja2 import Markup, escape

from flask_login import login_required, current_user
from flask_principal import Permission, RoleNeed

from sqlalchemy import and_
from sqlalchemy.sql import select
from wtforms import Form, StringField, BooleanField, validators

from ..core.backwardcompat import *
# from ..core.dump_html import html
from ..core.html_helpers import parse_input
from ..models import User

from ..a import app, db


# ===== Roles =====

admin_permission = Permission(RoleNeed('admin'))


# ===== Models =====

relationship_user_app = db.Table('rs_user_app',
    db.Column('_user_id', db.Integer, db.ForeignKey('user.id'), nullable=False),
    db.Column('_app_id', db.Integer, db.ForeignKey('app.id'), nullable=False),
#   db.PrimaryKeyConstraint('_user_id', '_app_id'),
)


class RS_App(db.Model):       # Rev. 2016-07-23
    __tablename__ = 'rs_user_app'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    _user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    _app_id = db.Column(db.Integer, db.ForeignKey('app.id'), nullable=False)
    token = db.Column(db.String, nullable=False, default='')
    sticked = db.Column(db.Boolean, nullable=False, default=True)
    options = db.Column(db.PickleType, nullable=False, default={})
    attached = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self):
        self.token = self.suit_code(self._user_id, self._app_id)

    def get_token(self, user, app):
    #   rnd = datetime.now().strftime("%Y%m%d%H%M%S.%f")
        rnd = random.randint(0, 100000000000000)
        return hashlib.md5("{0}_{1}_{2}".format(rnd, user, app)).hexdigest()

    def suit_code(self, user, app):
        double = True
        while double:
            token = self.get_token(user, app)
            double = RS_App.query.filter_by(token=token).first()

        return token


class App(db.Model):          # Rev. 2016-07-12
    __tablename__ = 'app'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    description = db.Column(db.String, nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, id, name, description=''):
        self.id = id
        self.name = name.lower()
        self.description = description


User.ext_apps = db.relationship('App', secondary=relationship_user_app,
                backref=db.backref('user', lazy='dynamic'))

db.create_all()


# ===== Forms =====

class AddAppForm(Form):
    name = StringField('Name *', [
        validators.Length(min=6, max=40)
    ])
    description = StringField('Description')

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False

        if not re.match('^[A-Za-z][\w.]*$', self.name.data):
            self.name.errors.append('All characters in the string must be alphanumeric or dot with underline')
            return False

        app = App.query.filter_by(name=self.name.data).first()
        if app:
            self.name.errors.append('App with the same name already registered')
            return False

        return True


# ===== Interface =====

def init_rs_user_app(user, app):
    s = relationship_user_app.update(values=dict(
          token = suit_code(user.id, app.id),
        )).where(
          and_(relationship_user_app.c._user_id == user.id,
          relationship_user_app.c._app_id == app.id)
        )
    res = db.session.execute(s)
    db.session.commit()


def update_token(user, app):
    s = relationship_user_app.update(values=dict(
          token = suit_code(user.id, app.id),
        )).where(
          and_(relationship_user_app.c._user_id == user.id,
          relationship_user_app.c._app_id == app.id)
        )
    res = db.session.execute(s)
    db.session.commit()


def get_token(user, app):
#   rnd = datetime.now().strftime("%Y%m%d%H%M%S.%f")
    rnd = random.randint(0, 100000000000000)
    return hashlib.md5("{0}_{1}_{2}".format(rnd, user, app)).hexdigest()


def suit_code(user, app):
    double = True
    while double:
        token = get_token(user, app)
#       double = RS_App.query.filter_by(token=token).first()

        s = select('*').select_from(relationship_user_app).\
              where(relationship_user_app.c.token == token)
        res = db.session.execute(s)
        double = res.first()

    return token


def get_user(app_id, token):
    s = select([relationship_user_app.c._user_id,
               relationship_user_app.c._app_id]).select_from(relationship_user_app).\
          where(relationship_user_app.c.token == token)
    res = db.session.execute(s)
    row = res.first()
    if row:
        _user_id, _app_id = row
        if app_id == _app_id:
            user = User.query.filter_by(id=_user_id).first()
            return user


# ===== Routes =====

@app.route('/app<int:id>', methods=['GET', 'POST'])
@login_required
def ext_user_app(id):
    form = AddAppForm(request.form)
    if request.method == 'POST' and form.validate():
        app = App(
            id = id,
            name = form.name.data,
            description = form.description.data,
        )
        db.session.add(app)
        db.session.commit()

        flash('App created!')

    app = App.query.filter_by(id=id).first()
    if app:
        if 'attach' in request.args:
            current_user.ext_apps.append(app)
            db.session.commit()

            init_rs_user_app(current_user, app)
            return redirect(url_for('ext_user_app', id=id))

        elif 'update' in request.args:
            update_token(current_user, app)
            return redirect(url_for('ext_user_app', id=id))

    else:
        flash('App is not created yet!')

        p_admin = admin_permission.can()
        return render_template('extensions/user_app/add_app.html',
                 title = '',
                 p_admin = p_admin,
                 form = form,
#                debug = html(table_info),
               )

    s = select('*').select_from(relationship_user_app).where(
          and_(relationship_user_app.c._user_id == current_user.id,
          relationship_user_app.c._app_id == app.id)
        )

    res = db.session.execute(s)
    user_app = res.first()
    if user_app:
        user_app = dict(user_app.items())

        options = user_app.pop('options')
    else:
        options = {}

    names = [i.name for i in App.__table__.c]
    row = [app.__dict__.get(i) for i in names]
    app = dict((zip(names, row)))

    return render_template('extensions/user_app/index.html',
             title = 'Options',
             app = app,
             user_app = user_app,
             options = options,
#            debug = html(table_info),
           )


@app.route('/admin/apps')
@login_required
@admin_permission.require(403)
def ext_user_app_apps():
    s = App.query
    total = s.count()

    apps = s.all()
    names = [i.name for i in App.__table__.c]
    rows = []
    for app in apps:
        row = []
        for i in names:
            if i == 'name':
                row.append(Markup('<a href="/app{0}">{1}</a>'.format(app.id, escape(app.name))))
            else:
                row.append(app.__dict__.get(i))

        rows.append(row)

    return render_template('dump_table.html',
             title = 'Apps',
             names = names,
             rows = rows,
             total = total,
           )


@app.route('/admin/user_apps', methods=['GET', 'POST'])
@login_required
@admin_permission.require(403)
def ext_user_app_users():
    if request.method == 'POST':
        action = request.form.get('action')
        result = 'omitted'
        message = ''

        if action == 'toggle_record':
            id = request.form.get('id')
            app_id = request.form.get('app_id')
            checked = request.form.get('checked')
            checked = True if checked == 'true' else False
            if id:
                user = User.query.filter_by(id=id).first()
                app = App.query.filter_by(id=app_id).first()
                if user and app:
                    if checked:
                        if app in user.ext_apps:
                            return jsonify(action=action, result='rejected', message='The app is already attached.')

                        user.ext_apps.append(app)
                        result = 'accepted'

                    else:
                        if app not in user.ext_apps:
                            return jsonify(action=action, result='rejected', message='The app is not attached.')

                        user.ext_apps.remove(app)
                        result = 'accepted'

        return jsonify(action=action, result=result, message=message)

    users = User.query.all()
    apps = App.query.all()
    total = len(users)

    names = ['id', 'email']
    for app in apps:
        names.append(app.id)

    rows = []
    for user in users:
        row = [user.id, escape(user.email)]

        for app in apps:
            row.append(parse_input('', app in user.ext_apps, 'toggle_record',
                id = user.id,
                app_id = app.id,
            ))

        rows.append(row)

    return render_template('admin/table_unsafe.html',
             title = 'User apps',
             names = names,
             rows = rows,
             total = total,
           )
