#!/usr/bin/env python
# coding=utf-8
# Stan 2013-05-15, 2016-04-24

from __future__ import ( division, absolute_import,
                         print_function, unicode_literals )

import os, logging
from flask import Flask, g, url_for, render_template, send_from_directory, abort, __version__
from sqlalchemy.sql import select

from .ext.backwardcompat import *
from .ext.db import initDb
from .ext.dump_html import html
from .ext.fileman import list_files
from .ext.settings import Settings


app = Flask(__name__, static_url_path='')


def get_conn():
    if 'engine' not in g:
        s = Settings()
        g.db_uri = "{0}:///{1}/{2}".format('sqlite', s.system.path, 'xls0p3.sqlite')
        g.engine, g.metadata, g.relationships = initDb(g.db_uri)
    return g.engine.connect()


@app.route("/")
def hello():
    return app.send_static_file('index.html')


@app.route('/user/<username>')
def profile(username):
    return 'User {0}'.format(username)


@app.route('/login')
def login():
    return ''


@app.route('/debug')
def view_debug():
    if not app.debug:
        abort(404)

    output = []
    for rule in app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        methods = ','.join(rule.methods)
        url = url_for(rule.endpoint, **options)
        output.append([rule.endpoint, methods, url])

    return render_template('view_debug.html',
             title = 'Url mapping',
             urls=sorted(output),
           )


@app.route('/test/')
@app.route('/test/<path:path>')
def view_test(path=''):
    if not app.debug:
        abort(404)

    if not path or path[-1] == '/':
        test_url = '/test/{0}'.format(path)
        dirlist, filelist = list_files(test_url, app.root_path)
        return render_template('view_test.html',
                 title = 'Testing directory',
                 path = test_url,
                 dirlist = dirlist,
                 filelist = filelist,
               )
    else:
        return send_from_directory(os.path.join(app.root_path, 'test'), path)
#       return send_from_directory('test', path)


@app.route('/ver')
def view_ver():
    if not app.debug:
        abort(404)

    return __version__


@app.route('/app')
def view_app():
    if not app.debug:
        abort(404)

    return html(app)


@app.route('/g')
def view_g():
    if not app.debug:
        abort(404)

    get_conn()
    return html(g)


@app.route('/rel')
def view_rel():
    if not app.debug:
        abort(404)

    get_conn()
    return html(g.relationships)


@app.route('/dbinfo/')
def view_dbinfo():
    if not app.debug:
        abort(404)

    get_conn()
#   return g.db_uri + '<br />' + html(g.metadata)
#   return render_template('dump_dict.html', obj=g.tables)
    return render_template('view_dbinfo.html',
             title = 'Databases info',
             uri=g.db_uri,
             dbs=g.metadata.tables.keys(),
             debug=html(g.metadata),
           )


@app.route('/dbinfo/<table>')
def view_tableinfo(table=None):
    if not app.debug:
        abort(404)

    get_conn()
    if table in g.metadata.tables.keys():
        return html(g.metadata.tables.get(table))
    else:
        return 'No such table!'


@app.route('/db/')
def view_db():
    get_conn()
    return render_template('view_db.html', 
             title = 'Databases',
             dbs = g.metadata.tables.keys(),
           )


@app.route('/db/<table1>/')
@app.route('/db/<table1>/<table2>/')
@app.route('/db/<table1>/<table2>/<table3>/')
@app.route('/db/<table1>/<table2>/<table3>/<table4>/')
@app.route('/db/<table1>/<table2>/<table3>/<table4>/<table5>/')
def view_table(table1=None, table2=None, table3=None, table4=None, table5=None):
    conn = get_conn()

    # Обратный порядок - не менять!
    tables = [i for i in [table5, table4, table3, table2, table1] if i]

    mtables = [g.metadata.tables.get(i) for i in tables]

    mcolumns = []
    for i in mtables:
        mcolumns.extend(j for j in i.c if not j.foreign_keys and not j.primary_key and j.name[0] != '_')

    offset = 0
    limit = 100
    colspan = len(mcolumns)
    s = select(mcolumns, offset=offset, limit=limit, use_labels=True)
    s_count = select(mtables, use_labels=True)

    error = None
    mtable = g.metadata.tables.get(table1)

    l = len(tables) - 1
    for i in range(l):
        for j in mtables[l - i].foreign_keys:
            if j.column.table == mtables[l - i - 1]:
                mtable = mtable.join(mtables[l - i - 1], j.parent==j.column)
                break
        else:
            error = 'Error!'

    result = conn.execute(s.select_from(mtable))
    rows = [row for row in result]

    count = conn.execute(s_count.select_from(mtable).count())
    count = count.first()[0]

    names = [[column.table.name, column.name] for name, column in s._columns_plus_names]
    extratables = [i.column.table.name for i in s_count.foreign_keys]   # s_count!
    lasttable = tables[0] if len(tables) > 1 else None
    return render_template('view_table.html',
             title = 'Database: {0}'.format(table1),
             count = count,
             offset = offset,
             limit = limit,
             colspan = colspan,
             rows = rows,
             names = names,
             tables = tables,
             extratables = extratables,
             lasttable = lasttable,
             error = error,
             debug = unicode(s),
           )



if __name__ == "__main__":
    app.run(debug=True)
