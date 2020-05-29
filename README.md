# pri3o-dmenu-desktop

## Description
**pri3o-dmenu-desktop** is a drop-in replacement for 
[Michael Stapelberg](https://github.com/stapelberg)'s `i3-dmenu-desktop`
that adds simple application priorization.
It supports all options present in `i3-dmenu-desktop` and a few more.

At this point priority is simply the absolute number times the program was run.
For example a program ran three times has a higher priority than a program only
run twice. It's very simple but pretty effective. In the future I might add a
time-based component as well.

The priority data is stored in a sqlite database in `$XDG_CONFIG_HOME/pri3o-dmenu-desktop/dmenu.db`
(defaults to `~/.config/pri3o-dmenu-desktop/dmenu.db`)
but a custom location can be specified via command line parameter. A new db will be
create if it does not exist yet.

## Requirements
To run this you need Python 3, all used libraries should be present in the 
standard distribution. Python 3 should already be present in any modern, 
non-minimal distribution. For older/LTS distributions (e.g. CentOS 7) you may
need to install it.

For RedHat based distros this can be done via:
```
yum install python3
```

For Debian based distros use:
```
apt install python3
```

## Installing
The easiest way to install is using `pip3`:
```
pip3 install pri3o_dmenu_desktop
```

## Running
Just run using
```
pri3o-dmenu-desktop [OPTIONS]
```
If run without parameters, will behave like `i3-dmenu-desktop` without parameters.
The optional commandline parameters are:
- `-d, --database=PATH` path to database file; default `$XDG_CONFIG_HOME/pri3o-dmenu-desktop/dmenu.db`
- `-e, --entry-type=TYPE` display "Name" (TYPE=name), "Exec" (TYPE=command) or .desktop filename (TYPE=filename) in dmenu, default `name`
- `-l, --locale=LOCALE` use LOCALE (e.g. `en_GB`) for localisation of "Name", default is system locale
- `-m, --dmenu=COMMAND` run this command for dmenu, default `dmenu -i`
- `-t, --term=COMMAND` use this command for programs that need to be run in a terminal, default `i3-sensible-terminal -e`

## Speed
As some people may wonder about how fast it is:
```
 % time pri3o-dmenu-desktop --dmenu=/bin/false
pri3o-dmenu-desktop --dmenu=/bin/false  0,06s user 0,01s system 99% cpu 0,070 total

 % time i3-dmenu-desktop --dmenu=/bin/false
i3-dmenu-desktop --dmenu=/bin/false  0,11s user 0,01s system 99% cpu 0,114 total

 % time j4-dmenu-desktop --dmenu=/bin/false
j4-dmenu-desktop --dmenu=/bin/false  0,00s user 0,00s system 97% cpu 0,006 total
```
On my system (SSD-only) it is slightly faster than `i3-dmenu-desktop`, but still
much slower than `j4-dmenu-desktop`. For all practical purposes these
differences should negligible unless you have a lot of applications and/or
a slow hard drive.
