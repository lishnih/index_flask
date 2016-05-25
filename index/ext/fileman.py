#!/usr/bin/env python
# coding=utf-8
# Stan 2016-05-22

from __future__ import ( division, absolute_import,
                         print_function, unicode_literals )

import os


def list_files(path, root):
    if root:
        fullpath = "{0}{1}".format(root, path)

    dirlist = []
    filelist = []
    try:
        ldir = os.listdir(fullpath)
    except OSError:
        pass
    else:
        for name in ldir:
            fullname = os.path.join(fullpath, name)
            url = '{0}{1}'.format(path, name)
            if os.path.isdir(fullname):
                dirlist.append([name, url])
            else:
                filelist.append([name, url])
    return dirlist, filelist