# -*- coding: utf-8 -*-
"""Navigation helper for the ATV Minimal title pages (windows 1130-1134).

The skin passes the id of the container whose focused item was selected; the
script reads that item's type and TMDb id itself, so titles with commas or
quotes never have to go through builtin arguments.

Each title page N shows Skin.String(DetailTypeN) (movie|tv) / Skin.String(DetailIDN).
Opening a title from page N fills page N+1 and opens it, so Kodi's normal Back
returns to the previous title. The last page is reused in place.

Usage:
    RunScript(special://skin/extras/details.py,open,<containerid>)
    RunScript(special://skin/extras/details.py,person,<containerid>)

Cast members open the search screen's twin (1121) pre-filled with that person, so Back
returns to the title page they came from.
"""
import sys
from urllib.parse import quote_plus

import xbmc
import xbmcgui

FIRST_PAGE = 1130  # Custom_1130..1134; Kodi reports them as 11130..11134
PAGES = 5
ACTOR_SEARCH = 1121  # copy of the search screen used for cast members


def info(label):
    return xbmc.getInfoLabel(label)


def set_string(name, value):
    if value:
        value = value.replace('\\', '\\\\').replace('"', '\\"')
        xbmc.executebuiltin(f'Skin.SetString({name},"{value}")')
    else:
        xbmc.executebuiltin(f'Skin.Reset({name})')


def item_type_and_id(container):
    prefix = f'Container({container}).ListItem'
    dbtype = info(f'{prefix}.DBType')
    if dbtype in ('episode', 'season'):
        tmdb_id = info(f'{prefix}.Property(tvshow.tmdb_id)') or info(f'{prefix}.UniqueID(tmdb)')
        return 'tv', tmdb_id
    tmdb_id = info(f'{prefix}.UniqueID(tmdb)') or info(f'{prefix}.Property(tmdb_id)')
    return ('tv' if dbtype == 'tvshow' else 'movie'), tmdb_id


def open_details(container):
    item_type, tmdb_id = item_type_and_id(container)
    if not tmdb_id:
        return
    window = xbmcgui.getCurrentWindowId() - 10000
    current = window - FIRST_PAGE  # page index, or out of range
    on_page = 0 <= current < PAGES
    if on_page:
        page = min(current + 1, PAGES - 1)
    elif window == ACTOR_SEARCH:  # search opened from a title page's cast: go one page deeper
        page = min(int(info('Skin.String(SearchFromPage)') or -1) + 1, PAGES - 1)
    else:
        page = 0
    set_string(f'DetailType{page}', item_type)
    set_string(f'DetailID{page}', tmdb_id)
    if on_page and page == current:  # deepest page: show the new title in place
        xbmc.executebuiltin('SetFocus(9601)')
    else:
        xbmc.executebuiltin(f'ActivateWindow({FIRST_PAGE + page})')


def open_person(container):
    prefix = f'Container({container}).ListItem'
    name = info(f'{prefix}.Label')
    person_id = info(f'{prefix}.UniqueID(tmdb)')
    if not person_id:
        return
    # Pre-fill the actor search (window 1121, strings with a "B" suffix) with this person
    set_string('SearchQueryB', name.lower())
    set_string('SearchQueryURLB', quote_plus(name.lower()))
    set_string('SearchPersonIDB', person_id)
    set_string('SearchPersonNameB', name)
    page = xbmcgui.getCurrentWindowId() - 10000 - FIRST_PAGE
    set_string('SearchFromPage', str(page) if 0 <= page < PAGES else '')
    xbmc.executebuiltin(f'ActivateWindow({ACTOR_SEARCH})')
    xbmc.executebuiltin('SetFocus(8120,0,absolute)')  # start on their movies


def main():
    args = sys.argv[1:]
    action = args[0] if args else ''
    if action == 'open' and len(args) > 1:
        open_details(args[1])
    elif action == 'person' and len(args) > 1:
        open_person(args[1])


main()
