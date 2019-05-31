#!/usr/bin/env python
#coding: UTF-8

"""
Bootstraping seafile server, letsencrypt (verification & cron job).
"""

import argparse
import os
from os.path import abspath, basename, exists, dirname, join, isdir, islink
import shutil
import sys
import uuid
import time

from utils import (
    call, get_conf, get_install_dir, loginfo,
    get_script, render_template, get_seafile_version, eprint,
    cert_has_valid_days, get_version_stamp_file, update_version_stamp,
    wait_for_mysql, wait_for_nginx, read_version_stamp
)

seafile_version = get_seafile_version()
installdir = get_install_dir()
topdir = dirname(installdir)
shared_seafiledir = '/shared/seafile'
nginx = '/nginx'
generated_dir = '/bootstrap/generated'

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parse-ports', action='store_true')

    return ap.parse_args()

def is_https():
    return get_conf('SEAFILE_SERVER_LETSENCRYPT', 'false').lower() == 'true'

def init_seafile_server():
    version_stamp_file = get_version_stamp_file()
    if exists(join(shared_seafiledir, 'seafile-data')):
        if not exists(version_stamp_file):
            update_version_stamp(os.environ['SEAFILE_VERSION'])
        # sysbol link unlink after docker finish.
        latest_version_dir='/opt/seafile/seafile-server-latest'
        current_version_dir='/opt/seafile/' + get_conf('SEAFILE_SERVER', 'seafile-server') + '-' +  read_version_stamp()
        if not exists(latest_version_dir):
            call('ln -sf ' + current_version_dir + ' ' + latest_version_dir)
        loginfo('Skip running setup-seafile.sh because there is existing seafile-data folder.')
        return False

    loginfo('Now running setup-seafile.sh in auto mode.')
    env = {
        'SERVER_NAME': 'seafile',
        'SERVER_IP': get_conf('SEAFILE_SERVER_HOSTNAME', 'seafile.example.com'),
    }

    setup_script = get_script('setup-seafile.sh')
    call('{} auto -n seafile'.format(setup_script), env=env)

    domain = get_conf('SEAFILE_SERVER_HOSTNAME', 'seafile.example.com')
    proto = 'https' if is_https() else 'http'
    with open(join(topdir, 'conf', 'seahub_settings.py'), 'a+') as fp:
        fp.write('\n')
        fp.write('FILE_SERVER_ROOT = "{proto}://{domain}/seafhttp"'.format(proto=proto, domain=domain))
        fp.write('\n')

    # By default ccnet-server binds to the unix socket file
    # "/opt/seafile/ccnet/ccnet.sock", but /opt/seafile/ccnet/ is a mounted
    # volume from the docker host, and on windows and some linux environment
    # it's not possible to create unix sockets in an external-mounted
    # directories. So we change the unix socket file path to
    # "/opt/seafile/ccnet.sock" to avoid this problem.
    with open(join(topdir, 'conf', 'ccnet.conf'), 'a+') as fp:
        fp.write('\n')
        fp.write('[Client]\n')
        fp.write('UNIX_SOCKET = /opt/seafile/ccnet.sock\n')
        fp.write('\n')

    # After the setup script creates all the files inside the
    # container, we need to move them to the shared volume
    #
    # e.g move "/opt/seafile/seafile-data" to "/shared/seafile/seafile-data"
    files_to_copy = ['conf', 'ccnet', 'seafile-data', 'seahub-data', 'pro-data', 'seahub.db', 'logs']
    for fn in files_to_copy:
        src = join(topdir, fn)
        dst = join(shared_seafiledir, fn)
        if not exists(dst) and exists(src):
            shutil.move(src, shared_seafiledir)
            call('ln -sf ' + join(shared_seafiledir, fn) + ' ' + src)

    call('rsync -axk --delete --exclude "CACHE" ' + join(topdir, 'seafile-server-' + seafile_version, 'seahub', 'media') + ' ' + nginx)
    call('rsync -ax --delete ' + join(topdir, 'seahub-data', 'avatars') + ' ' + join(nginx, 'media'))
    call('rsync -ax --delete ' + join(topdir, 'seahub-data', 'custom') + ' ' + join(nginx, 'media'))

    if not exists(join(nginx, 'media', 'CACHE')):
        call('mkdir -p ' + join(nginx, 'media', 'CACHE'))

    if not islink(join(topdir, 'seafile-server-' + seafile_version, 'seahub', 'media', 'CACHE')):
        call('ln -sf ' + join(nginx, 'media', 'CACHE') + ' ' + join(topdir, 'seafile-server-' + seafile_version, 'seahub', 'media', 'CACHE'))

    loginfo('Updating version stamp')
    update_version_stamp(os.environ['SEAFILE_VERSION'])

    return True

def recreate_ln():
    files_to_copy = ['conf', 'ccnet', 'seafile-data', 'seahub-data', 'pro-data', 'seahub.db', 'logs']
    for fn in files_to_copy:
        src = join(topdir, fn)
        dst = join(shared_seafiledir, fn)
        if exists(dst) and not exists(src):
            call('ln -sf ' + join(shared_seafiledir, fn) + ' ' + src)
        elif not exists(dst) and exists(src):
            shutil.move(src, shared_seafiledir)
            call('ln -sf ' + join(shared_seafiledir, fn) + ' ' + src)

    call('rsync -axk --delete --exclude "CACHE" ' + join(topdir, 'seafile-server-' + seafile_version, 'seahub', 'media') + ' ' + nginx)
    call('rsync -ax --delete ' + join(topdir, 'seahub-data', 'avatars') + ' ' + join(nginx, 'media'))
    call('rsync -ax --delete ' + join(topdir, 'seahub-data', 'custom') + ' ' + join(nginx, 'media'))

    if not exists(join(nginx, 'media', 'CACHE')):
        call('mkdir -p ' + join(nginx, 'media', 'CACHE'))

    if not islink(join(topdir, 'seafile-server-' + seafile_version, 'seahub', 'media', 'CACHE')):
        call('ln -sf ' + join(nginx, 'media', 'CACHE') + ' ' + join(topdir, 'seafile-server-' + seafile_version, 'seahub', 'media', 'CACHE'))
