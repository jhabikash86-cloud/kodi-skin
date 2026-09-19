# -*- coding: utf-8 -*-
"""Search helper for the ATV Minimal search screen (window 1120).

Letters and digits are appended by the skin itself (instant). This script handles
the edits the skin engine can't do on its own: space, delete, clear and typing with
Kodi's keyboard. It keeps two skin strings in sync:

    SearchQuery     what the user sees
    SearchQueryURL  the same text, URL-encoded, used in the TMDb Helper paths

Window 1121 (the actor search opened from a title page) keeps its own copies of these
strings with a "B" suffix, so the two search screens never overwrite each other.

Usage: RunScript(special://skin/extras/search.py,<space|delete|clear|keyboard>)
"""
import sys
from urllib.parse import quote_plus

import xbmc
import xbmcgui


def _escape(value):
    return value.replace('\\', '\\\\').replace('"', '\\"')


SUFFIX = 'B' if xbmcgui.getCurrentWindowId() == 11121 else ''


def _set(name, value):
    name += SUFFIX
    if value:
        xbmc.executebuiltin(f'Skin.SetString({name},"{_escape(value)}")')
    else:
        xbmc.executebuiltin(f'Skin.Reset({name})')


def set_query(query):
    query = query.lstrip()
    _set('SearchQuery', query)
    _set('SearchQueryURL', quote_plus(query) if query.strip() else '')
    # A new query always clears an actor that was picked from the previous results
    _set('SearchPersonID', '')
    _set('SearchPersonName', '')


def main():
    action = sys.argv[1].lower() if len(sys.argv) > 1 else ''
    query = xbmc.getInfoLabel(f'Skin.String(SearchQuery{SUFFIX})')

    if action == 'space':
        if query and not query.endswith(' '):
            set_query(query + ' ')
    elif action == 'delete':
        set_query(query[:-1])
    elif action == 'clear':
        set_query('')
    elif action == 'keyboard':
        typed = xbmcgui.Dialog().input('Search movies, TV shows and people', defaultt=query)
        if typed:  # Dialog().input returns '' on cancel, so keep the old query
            set_query(typed)


main()
