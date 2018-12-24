#!/usr/bin/env python
# coding=utf-8
# Stan 2018-09-13

from __future__ import (division, absolute_import,
                        print_function, unicode_literals)

from flask import request, redirect, url_for

from flask_login import login_required, current_user

from sqlalchemy.sql import select, func, text, column, table, and_

from requests.exceptions import *

from ..main import app, db
from ..core.cloud_interface import get_cloud_files
from ..core.functions import get_next
from ..core.render_response import render_ext
from ..core.source_task import source_task_create
from ..forms.source import AddSourceForm
from ..models.source import Source


# ===== Interface =====

def get_clouds(user):
    usersocialauth = table('social_auth_usersocialauth')
    user_id = column('user_id')
    s = select(['*'], user_id == user.id, usersocialauth)
    s_count = select([func.count()], user_id == user.id, usersocialauth)

    res = db.session.execute(s)
    total = db.session.execute(s_count).scalar()

    clouds = [i for i in res.fetchall() if i.provider in (
        'dropbox-oauth2',
        'google-oauth2',
        'yandex-oauth2',
    )]

    return total, clouds


def get_cloud(user, provider_name):
    usersocialauth = table('social_auth_usersocialauth')
    user_id = column('user_id')
    provider = column('provider')
    s = select(['*'], and_(user_id == user.id, provider == provider_name), usersocialauth)

    res = db.session.execute(s)

    return res.fetchone()


def get_provider_name(provider):
    if provider == 'dropbox-oauth2':
        return "Dropbox"
    elif provider == 'google-oauth2':
        return "Google Drive"
    elif provider == 'mailru-oauth2':
        return "Mail.Ru Cloud"
    elif provider == 'yandex-oauth2':
        return "Yandex Disk"
    else:
        return provider


# ===== Routes =====

@app.route('/accounts')
@login_required
def user_source_connect():
    return render_ext('home.html',
        user = current_user,
    )


@app.route('/sources')
@login_required
def user_sources():
    return render_ext('db/user_sources.html',
        sources = db.session.query(Source).filter_user().all(),
    )


@app.route('/source/configure', methods=['GET', 'POST'])
@login_required
def user_source_configure():
    uid = request.values.get('uid')
    name = request.values.get('name')
    result_m = 'ok'

    user_source = db.session.query(Source).filter_user().filter_by(uid=uid).first()
    if not user_source:
        result_m = 'error', "Источник данных не задан: {0}".format(name)
        return render_ext('base.html', result_m)

    return render_ext('db/user_source.html', result_m,
        source = user_source,
    )


@app.route('/source/interface', methods=['GET', 'POST'])
@login_required
def user_source_interface():
    result_m = 'ok'
    d = dict(format='json')

    action = request.values.get('action')
    if action == 'get_cloud_files':
        provider_name = request.values.get('provider')
        dir_ = request.values.get('dir')
        cloud = get_cloud(current_user, provider_name)
        try:
            d['rows'] = get_cloud_files(cloud, dir_)

        except ProxyError as e:   # > ConnectionError > RequestException > IOError
            result_m = 'error', 'Proxy Error!'
            d['debug'] = repr(e)

        except ReadTimeout as e:  # > Timeout > RequestException > IOError
            result_m = 'error', 'Read Timeout Error!'
            d['debug'] = repr(e)

        except RequestException as e:
            result_m = 'error', 'Request error!'
            d['debug'] = repr(e)

        except Exception as e:
            result_m = 'error', 'General error!'
            d['debug'] = repr(e)

    else:
        result_m = 'error', 'Action required!'

    return render_ext(None, result_m=result_m, **d)


@app.route('/source/append', methods=['GET', 'POST'])
@login_required
def user_source_append():
    total, clouds = get_clouds(current_user)
    if not total:
        return render_ext('base.html',
            html = 'No accounts connected! <a href="{0}">Connect accounts'.format(url_for('user_source_connect')),
        )

    providers = [[i.provider, get_provider_name(i.provider)] for i in clouds]

    form = AddSourceForm(request.form)
    result_m = 'ok'

    if request.method == 'POST':
        if form.validate():
            user_source = Source(
                name = form.name.data,
                provider = form.provider.data,
                path = form.path.data,
                path_id = form.path_id.data,
                user = current_user,
            )
            db.session.add(user_source)
            db.session.commit()

            source_task_create(user_source, 'scan_files', 'auto')

            result_m = 'ok', "Successfully append {0}".format(form.name.data)

        else:
            result_m = 'error', 'Invalid data!'

    return render_ext('db/append_source.html', result_m,
        form = form,
        total = total,
        providers = providers,
    )


@app.route('/source/delete', methods=['GET', 'POST'])
@login_required
def user_source_delete():
    uid = request.values.get('uid')
    name = request.values.get('name')
    result_m = 'ok'

    user_source = db.session.query(Source).filter_user().filter_by(uid=uid).first()
    if not user_source:
        result_m = 'error', "Источник данных не задан: {0}".format(name)
        return render_ext('base.html', result_m)

    user_source.deleted = True
    db.session.commit()

    return redirect(get_next(back=True))
