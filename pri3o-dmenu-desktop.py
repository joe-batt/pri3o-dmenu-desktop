#!/usr/bin/env python3
#
#  Copyright (c) 2020, Johannes Battenberg
# 
# This script is meant as a drop in replacement for i3-menu-desktop but
# includes simple priorization of applications via the absolute run count
# of an application. The count is stored in a sqlite db.
import os
import sqlite3
import glob
import locale
import re
import getopt
import sys

from subprocess import Popen, PIPE, STDOUT
from pathlib import Path

# Session Data object, short name because of lazyness/readability
_s={}

def init_session_data(argv):
    config_base()
    _s['db'] = _s["config_base"]+'/dmenu.db'
    _s['locale'] = locale.LC_CTYPE
    parse_args(argv)

def config_base():
    """ get the base directory for config files, it uses
    $XDG_CONFIG_HOME/pri3o_dmenu_desktop and falls back to
    ~/.config/pri3o_dmenu_desktop """
    if 'XDG_CONFIG_HOME' in os.environ:
        _s['config_base'] = os.environ['XDG_CONFIG_HOME']+"/pri3o_dmenu_desktop"
    else:
        _s['config_base'] = os.environ['HOME']+"/.config/pri3o_dmenu_desktop"

    if not os.path.isdir(_s['config_base']):
        Path(_s['config_base']).mkdir(parents=True, exist_ok=True)


def parse_args(argv):
    """ parse given commandline arguments"""
    opts, args = getopt.getopt(argv,"d:l:h")
    for opt, arg in opts:
        # show help
        if opt == '-h':
            print('Usage pri3o_dmenu_desktop.py [-d <db file>] [-l <locale>]')
            exit()
        # use custom db location
        elif opt == '-d':
            print("d", arg)
            _s['db'] = os.path.expanduser(arg)
        # use custom locale
        elif opt == '-l':
            _s['locale'] = arg

def parse_exec(ex):
    """ parse %-Flags in desktop, for now they are simply ignored """
    # Remove deprecated flags
    ex = re.sub(r'%[dDnNvm]', '', ex)
    # for now ignore all other flags as well
    ex = re.sub(r'%[fFuUcik]', '', ex)
    return ex

def parse_desktop(content):
    """ parse all entries of the [Desktop Entry] section into a dictionary.
        return None if first line in file is not [Desktop Entry] """
    data = {}
    # strip all lines, remove empty lines and comments
    content = list(map(lambda x: x.strip(), content))
    content = list(filter(None, content))
    content = list(filter(lambda x: not x.startswith("#"), content))
    if content[0] != "[Desktop Entry]":
        return None

    del content[0]
    # fill data into dict, break on new block
    for line in content:
        if line.startswith('['):
            break
        k, v = line.split("=", 1)
        data[k]=v
    return data

def conn_db():
    """  connect to DB """
    _s['conn'] = sqlite3.connect(_s['db'])
    _s['c'] = _s['conn'].cursor()
    # return conn, c

def init_db():
    # initialize new database
    conn_db()
    _s['c'].execute('CREATE TABLE prio (count int, app text)')
    _s['conn'].commit()
    _s['conn'].close()

def gen_lang_strings():
    """ Set language names for .desktop parsing, first full local (e.g en_US),
        second the more generic (e.g. en) """
    lang = [locale.setlocale(_s['locale']).split(".")[0]]
    lang.append(lang[0].split("_")[0])
    _s['lang'] = lang

    # generate key names from lang, use Name as fallback
    lang_keys = ["Name[{}]".format(l) for l in lang]
    lang_keys.append("Name")
    _s['lang_keys'] = lang_keys

def get_search_dirs():
    """ build list of XDG directories to search """
    # get XDG dirs
    if 'XDG_DATA_HOME' in os.environ:
        xdg_data_home = os.environ['XDG_DATA_HOME']
    else:
        xdg_data_home = os.environ['HOME']+"/.local/share"

    if 'XDG_DATA_DIRS' in os.environ:
        xdg_data_dirs = os.environ['XDG_DATA_DIRS']
    else:
        xdg_data_dirs = '/usr/local/share/:/usr/share/'

    # get app dirs, make sure the personal dir comes last as later entries
    # will overwrite existing ones for apps with identical names
    searchdirs =[d+'/applications' for d in xdg_data_dirs.split(":")]
    searchdirs.extend([xdg_data_home+'/applications'])
    return searchdirs

def get_desktop_list():
    """ generate a list of all .desktop files """
    searchdirs = get_search_dirs()
    # find all desktop files
    files = [[f for f in glob.glob(d+"/*.desktop")] for d in searchdirs]
    return [y for x in files for y in x]

def is_visible(app_data):
    """ check if app should be visible, which is pretty much everything
        which has neither Hidden nor NoDisplay set to true """
    if 'Hidden' in app_data.keys() and app_data['Hidden'] == "true":
        return False
    if 'NoDisplay' in app_data.keys() and app_data['NoDisplay'] == "true":
        return False
    return True

def fetch_apps():
    """ fetch the actual app info and parse it into a dictionary with name
        as key, apart from that app prio and command are stored."""
    _s['apps']={}
    # build app list, generate dictionary with name as key
    for f in get_desktop_list():
        content = Path(f).read_text().split('\n')
        data = parse_desktop(content)
        if data is not None:
#        data["_location"] = f
            # ignore Hidden and NoDisplay
            if is_visible(data):
                # parse name
                name_idx = list(map(lambda x: x in data.keys(), _s['lang_keys'])).index(True)
                name = data[_s['lang_keys'][name_idx]]
        
                # set prio in app data, prio needs to be lower case
                prio = (0, name.lower())
                if name.lower() in _s['db_info'].keys():
                    prio = _s['db_info'][name.lower()]
                _s['apps'][name] = {"name": name, "exec": data["Exec"], "prio": prio}

def fetch_db_info():
    """ load current info from database """
    _s["c"].execute('SELECT * FROM prio')
    _s["db_info"] = {e[1]: e for e in _s['c'].fetchall()}

def run_dmenu():
    """ display dmenu and return choice """
    # build and sort applist from app.keys()
    applist=list(_s["apps"].keys())
    applist.sort(key=lambda x: _s["apps"][x]["prio"])

    # run dmenu and read choice
    p = Popen(["dmenu", "-i"], stdout=PIPE, stdin=PIPE, stderr=PIPE)
    choice = p.communicate(input=bytearray("\n".join(applist), encoding='utf-8'))
    return choice[0].decode()[:-1]

def update_prio(choice):
    """ update prio in db, add new entry if needed. Priority is lowered
        as this helps python's natural sort order."""
    count, app = _s["apps"][choice]["prio"]
    count-=1
    if choice.lower() in _s["db_info"].keys():
        _s["c"].execute('UPDATE prio SET count=? WHERE app=?', (count, app))
    else:
        _s["c"].execute('INSERT INTO prio VALUES (?, ?)', (count, app))
    _s["conn"].commit()

def run_app(choice):
    """ run selected command """
    Popen(parse_exec(_s["apps"][choice]["exec"]).split())

def main(argv):
    init_session_data(argv)
    gen_lang_strings()
    # create new db if it's not present
    if not os.path.isfile(_s['db']):
        init_db()
    # fetch all entries from DB
    conn_db()
    fetch_db_info()
    fetch_apps()
    choice = run_dmenu()
    if choice == '':
        _s["conn"].close()
        exit()
    update_prio(choice)
    run_app(choice)


if __name__ == "__main__":
    main(sys.argv[1:])
