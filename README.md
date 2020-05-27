# pri3o-dmenu-desktop

## Description
This is meant as a drop-in replacement for Michael Stapelberg's `i3-dmenu-desktop`
and adds simple application priorization.
The generated menu sorts applications first by priority and alphabetically
second.

This is an early version, the basics are working, but there is still a lot of
stuff in missing:
- no config file yet
- no "Run in Terminal" support
- no parsing of field codes in `Exec`
- no passing of options to dmenu
- probably more

At this point priority is simply the absolute number times the program was run.
For example a program ran three times has a higher priority than a program only
run twice.

The priority data is stored in a sqlite database in `$XDG_CONFIG_HOME/pri3o_dmenu_desktop/dmenu.db`
(defaults to `~/.config/pri3o_dmenu_desktop/dmenu.db`)
but a custom location can be specified via command line parameter. A new db will be
create if it does not exist yet.

## Requirements
To run this you need Python 3 with the sqlite3 module, which should already
be present in a usual desktop setup.

## Running
The simplest way is to run without parameters
```
./pri3o-dmenu-desktop.py
```

In this case it will behave like `i3-dmenu-desktop` without parameters

Optional commandline parameters are:
- `-d </path/to/db>`: Path to custom DB location
- `-l <locale>`: Overwrite the system locale with the selected one, eg. `en_GB`
