# -*- coding: utf-8 -*-
"""The date windows the rows are built on, kept current.

Rows like "In Cinemas Now" (released in the last 45 days) or the charts (the last 18 months)
used to have their dates written into the XML by the generators, so they described the day
the skin was generated and drifted further out of date every day after. Now the XML asks for
$INFO[Window(home).Property(ATVDate.d45)] and this sets it: at startup, before Home builds a
single row, and again whenever the date changes (extras/prefetch.py calls refresh() each
minute). A row whose date changes simply loads again.

    RunScript(special://skin/extras/dates.py,startup)   from Startup.xml; then opens Kodi's
                                                         start window, whatever happens
"""
import datetime
import re
import sys

import xbmc
import xbmcgui

HOME = xbmcgui.Window(10000)
PREFIX = 'ATVDate.'
# name -> days back. Keep in step with DATE in tools/gen_home.py and tools/gen_browse.py.
WINDOWS = {'today': 0, 'd45': 45, 'd90': 90, 'd365': 365, 'd540': 540, 'd1095': 1095, 'd3650': 3650}
TOKEN = re.compile(r'\$INFO\[Window\(home\)\.Property\(ATVDate\.(\w+)\)\]')


def values(today=None):
    today = today or datetime.date.today()
    return {name: (today - datetime.timedelta(days=days)).isoformat() for name, days in WINDOWS.items()}


def refresh():
    """Set every window; only a property whose value changed is touched, so rows reload
    once a day at most."""
    for name, value in values().items():
        if HOME.getProperty(PREFIX + name) != value:
            HOME.setProperty(PREFIX + name, value)


def resolve(path):
    """A row path with its date tokens filled in - for scripts that read the XML."""
    now = values()
    return TOKEN.sub(lambda m: now.get(m.group(1), ''), path)


def main():
    if sys.argv[1:] == ['startup']:
        try:
            refresh()
        finally:
            xbmc.executebuiltin(f"ReplaceWindow({xbmc.getInfoLabel('System.StartupWindow') or 'home'})")
    else:
        refresh()


if __name__ == '__main__':
    main()
