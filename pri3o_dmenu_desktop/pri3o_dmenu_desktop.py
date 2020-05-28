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

class Pri3oDmenuDesktop:
    def __init__(self):
        # Session Data object, short name because of lazyness/readability
        self.get_config_base()
        self.ENTRY_TYPES = ["name", "command", "filename"]
        self.db = self.config_base+'/dmenu.db'
        self.locale = locale.LC_CTYPE
        self.dmenu_cmd = 'dmenu -i'
        self.entry_type = 'name'
        self.term = 'i3-sensible-terminal -e'
        self.parse_args()

    def get_config_base(self):
        """ get the base directory for config files, it uses
        $XDG_CONFIG_HOME/pri3o-dmenu-desktop and falls back to
        ~/.config/pri3o-dmenu-desktop """
        if 'XDG_CONFIG_HOME' in os.environ:
            self.config_base = os.environ['XDG_CONFIG_HOME']+"/pri3o-dmenu-desktop"
        else:
            self.config_base = os.environ['HOME']+"/.config/pri3o-dmenu-desktop"

        if not os.path.isdir(self.config_base):
            Path(self.config_base).mkdir(parents=True, exist_ok=True)

    def show_help(self):
        print("""Usage:
            pri3o-dmenu-desktop [OPTIONS]

    Options:
           -d, --database=PATH      path to database file;
                                    default '$XDG_CONFIG_HOME/pri3o-dmenu-desktop/dmenu.db'
           -e, --entry-type=TYPE    display "Name" (TYPE=name), "Exec" (TYPE=command)
                                    or .desktop filename (TYPE=filename) in dmenu,
                                    default 'name'
           -h, --help               display this message
           -l, --locale=LOCALE      use LOCALE (e.g. 'en_GB') for localisation of
                                    "Name", default is system locale
           -m, --dmenu=COMMAND      run this command for dmenu, default 'dmenu -i'
           -t, --term=COMMAND       use this command for programs that need to be run
                                    in a terminal, default 'i3-sensible-terminal -e'
    """)

    def parse_args(self):
        """ parse given commandline arguments"""
        opts, args = getopt.getopt(sys.argv[1:],"d:e:hl:m:t", ["database=", "dmenu=", 
                                   "entry-type=", "help", "locale=", "term="])
        for opt, arg in opts:
            if opt == '-h' or opt == "--help":
                show_help()
                exit()
            elif opt == '-d' or opt == '--database':
                self.db = os.path.expanduser(arg)
            elif opt == '-l' or opt == '--locale':
                self.locale = arg
            elif opt == '-m' or opt == '--dmenu':
                self.dmenu_cmd = arg
            elif opt == '-t' or opt == '--term':
                self.term = arg
            elif opt == '-e' or opt == '--entry-type':
                if arg in ENTRY_TYPES:
                    self.entry_type = arg
                else:
                    print("ERROR: invalid entry type: {}".format(arg))
                    exit(1)

    def parse_exec(self, ex):
        """ Parse %-Flags in desktop, for now they are simply ignored, also remove
        quotes around commands"""
        if ex.startswith('"') and ex.endswith('"'):
            ex = ex.strip('""')
        elif ex.startswith("'") and ex.endswith("'"):
            ex = ex.strip("'")

        # Remove deprecated flags
        ex = re.sub(r'%[dDnNvm]', '', ex)
        # for now ignore all other flags as well
        ex = re.sub(r'%[fFuUcik]', '', ex)
        return ex

    def parse_desktop(self, content):
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

    def conn_db(self):
        """  connect to DB """
        self.conn = sqlite3.connect(self.db)
        self.c = self.conn.cursor()
        # return conn, c

    def init_db(self):
        # initialize new database
        conn_db()
        self.c.execute('CREATE TABLE prio (count int, app text)')
        self.conn.commit()
        self.conn.close()

    def gen_lang_strings(self):
        """ Set language names for .desktop parsing, first full local (e.g en_US),
            second the more generic (e.g. en) """
        lang = [locale.setlocale(self.locale).split(".")[0]]
        lang.append(lang[0].split("_")[0])
        self.lang = lang

        # generate key names from lang, use Name as fallback
        lang_keys = ["Name[{}]".format(l) for l in lang]
        lang_keys.append("Name")
        self.lang_keys = lang_keys

    def get_search_dirs(self):
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

    def get_desktop_list(self):
        """ generate a list of all .desktop files """
        searchdirs = self.get_search_dirs()
        # find all desktop files
        files = [[f for f in glob.glob(d+"/*.desktop")] for d in searchdirs]
        return [y for x in files for y in x]

    def is_visible(self, app_data):
        """ check if app should be visible, which is pretty much everything
            which has neither Hidden nor NoDisplay set to true """
        if 'Hidden' in app_data.keys() and app_data['Hidden'] == "true":
            return False
        if 'NoDisplay' in app_data.keys() and app_data['NoDisplay'] == "true":
            return False
        return True

    def fetch_apps(self):
        """ fetch the actual app info and parse it into a dictionary with name
            as key, apart from that app prio and command are stored."""
        self.apps={}
        # build app list, generate dictionary with name as key
        for f in self.get_desktop_list():
            content = Path(f).read_text().split('\n')
            data = self.parse_desktop(content)
            if data is not None and self.is_visible(data):
                # parse name
                app_info = {}
                name_idx = list(map(lambda x: x in data.keys(), self.lang_keys)).index(True)
                name = data[self.lang_keys[name_idx]]

                app_info["name"] = name
                app_info["command"] = self.parse_exec(data["Exec"])

                app_info["terminal"] = False
                if 'Terminal' in data.keys() and data["Terminal"] == "true":
                    app_info["terminal"] = True
                    
                # basically do a basename <file> .desktop, python basename
                # does not support a suffix and will use split anyway
                app_info["filename"] = f.split("/")[-1].split(".")[0]
                key = app_info[self.entry_type]
        
                # set prio in app data, prio needs to be lower case
                app_info["prio"] = (0, key.lower())
                if name.lower() in self.db_info.keys():
                    app_info["prio"] = (self.db_info[name.lower()][0], key.lower())
                self.apps[key] = app_info

    def fetch_db_info(self):
        """ load current info from database """
        self.c.execute('SELECT * FROM prio')
        self.db_info = {e[1]: e for e in self.c.fetchall()}

    def run_dmenu(self):
        """ display dmenu and return choice """
        # build and sort applist from app.keys()
        applist=list(self.apps.keys())
        applist.sort(key=lambda x: self.apps[x]["prio"])

        # run dmenu and read choice
        p = Popen(self.dmenu_cmd.split(), stdout=PIPE, stdin=PIPE, stderr=PIPE)
        choice = p.communicate(input=bytearray("\n".join(applist), encoding='utf-8'))
        return choice[0].decode()[:-1].split("\n")[0]

    def update_prio(self, choice):
        """ update prio in db, add new entry if needed. Priority is lowered
            as this helps python's natural sort order."""
        count = self.apps[choice]["prio"][0]
        app = self.apps[choice]["name"]
        count-=1
        if app.lower() in self.db_info.keys():
            self.c.execute('UPDATE prio SET count=? WHERE app=?', (count, app))
        else:
            self.c.execute('INSERT INTO prio VALUES (?, ?)', (count, app))
        self.conn.commit()

    def run_app(self, choice):
        """ run selected command """
        app = self.apps[choice]
        
        if app["terminal"]:
            Popen("{} {}".format(self.term, app["command"]).split())
        else:
            Popen(app["command"].split())

    def main(self):
        self.gen_lang_strings()
        # create new db if it's not present
        if not os.path.isfile(self.db):
            init_db()
        # fetch all entries from DB
        self.conn_db()
        self.fetch_db_info()
        self.fetch_apps()
        choice = self.run_dmenu()
        if choice == '':
            self.conn.close()
            exit()
        self.update_prio(choice)
        self.run_app(choice)


if __name__ == "__main__":
    Pri3oDmenuDesktop().main()
