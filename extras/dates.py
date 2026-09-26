# -*- coding: utf-8 -*-
"""The date windows the rows are built on, kept current.

Rows like "In Cinemas Now" (released in the last 45 days) or the charts (the last 18 months)
used to have their dates written into the XML by the generators, so they described the day
the skin was generated and drifted further out of date every day after. Now the XML asks for
$INFO[Skin.String(ATVDate.d45)] and this sets it, and again whenever the date changes
(extras/prefetch.py calls refresh() each minute). A row whose date changes simply loads again.

The values are skin strings, so Kodi keeps them between runs and Home opens at once on
yesterday's - this runs alongside it and moves them on if the day has changed. They used to
be window properties, gone at every start, so Home waited for this script: two seconds of a
black screen on the Xbox, where starting Python is slow. Only the very first start of the
skin, with nothing saved yet, still waits for it.

    RunScript(special://skin/extras/dates.py,startup)   from Startup.xml; opens Kodi's start
                                                         window itself if Startup.xml could not
"""
import datetime
import re
import sys

import xbmc
import xbmcgui

PREFIX = 'ATVDate.'
# name -> days back. Keep in step with DATE in tools/gen_home.py and tools/gen_browse.py.
WINDOWS = {'today': 0, 'd45': 45, 'd90': 90, 'd365': 365, 'd540': 540, 'd1095': 1095, 'd3650': 3650}
# name -> years back, as a Trakt "years" range: y3 is this year and the two before, 2024-2026
YEARS = {'y3': 2}
TOKEN = re.compile(r'\$INFO\[Skin\.String\(ATVDate\.(\w+)\)\]')
STARTUP = 'Window.IsActive(12999)'   # Startup.xml, still showing: nothing was saved yet


def values(today=None):
    today = today or datetime.date.today()
    now = {name: (today - datetime.timedelta(days=days)).isoformat() for name, days in WINDOWS.items()}
    now.update({name: f'{today.year - back}-{today.year}' for name, back in YEARS.items()})
    return now


def refresh():
    """Set every window; only a value that changed is touched, so rows reload once a day
    at most."""
    for name, value in values().items():
        if xbmc.getInfoLabel(f'Skin.String({PREFIX}{name})') != value:
            xbmc.executebuiltin(f'Skin.SetString({PREFIX}{name},{value})')


def resolve(path):
    """A row path with its date tokens filled in - for scripts that read the XML."""
    now = values()
    return TOKEN.sub(lambda m: now.get(m.group(1), ''), path)


def main():
    if sys.argv[1:] == ['startup']:
        try:
            refresh()
        finally:
            if xbmc.getCondVisibility(STARTUP):
                xbmc.executebuiltin(f"ReplaceWindow({xbmc.getInfoLabel('System.StartupWindow') or 'home'})")
    else:
        refresh()


if __name__ == '__main__':
    main()
