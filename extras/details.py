# -*- coding: utf-8 -*-
"""Navigation helper for the ATV Minimal title pages (windows 1130-1134).

The skin passes the id of the container whose focused item was selected; the
script reads that item's type and TMDb id itself, so titles with commas or
quotes never have to go through builtin arguments.

Each title page N shows Skin.String(DetailTypeN) (movie|tv) / Skin.String(DetailIDN).
Opening a title from page N fills page N+1 and opens it, so Kodi's normal Back
returns to the previous title. The last page is reused in place.

Usage:
    RunScript(special://skin/extras/details.py,open,<containerid>[,<index>])
    RunScript(special://skin/extras/details.py,person,<containerid>)

The optional index is for the numbered Top 10 rows: their tiles are fixed controls bound
to absolute positions of a hidden list that never moves its own focus, so without it every
tile read position 0 and opened the same title.

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
    """Set a skin string and wait until Kodi reports it back.

    Skin.SetString runs asynchronously, so a window opened straight afterwards can build
    its container paths from the previous (or empty) value - that showed up as
    "tmdb_type=&tmdb_id=123" requests and an empty title page.
    """
    wanted = value or ''
    if value:
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        xbmc.executebuiltin(f'Skin.SetString({name},"{escaped}")')
    else:
        xbmc.executebuiltin(f'Skin.Reset({name})')
    for _ in range(100):  # up to ~2s; normally one or two loops
        if info(f'Skin.String({name})') == wanted:
            return
        xbmc.sleep(20)


# TMDb genre ids. TMDb Helper 6 only translates genre NAMES that exist for both movies
# and TV, so "Horror" or "Science Fiction" silently resolved to nothing; ids always work.
GENRE_IDS = {
    'action': 28, 'adventure': 12, 'animation': 16, 'comedy': 35, 'crime': 80,
    'documentary': 99, 'drama': 18, 'family': 10751, 'fantasy': 14, 'history': 36,
    'horror': 27, 'music': 10402, 'mystery': 9648, 'romance': 10749,
    'science fiction': 878, 'tv movie': 10770, 'thriller': 53, 'war': 10752, 'western': 37,
    'action & adventure': 10759, 'kids': 10762, 'news': 10763, 'reality': 10764,
    'sci-fi & fantasy': 10765, 'soap': 10766, 'talk': 10767, 'war & politics': 10768,
}


def list_prefix(container, index=None):
    """Container info prefix: the focused item, or a fixed position when index is given."""
    if index is None:
        return f'Container({container}).ListItem'
    return f'Container({container}).ListItemAbsolute({index})'


def genre_ids(container, index=None):
    """Comma separated TMDb genre ids (= all of them) for the item."""
    names = info(f'{list_prefix(container, index)}.Genre')
    ids = [str(GENRE_IDS[n.strip().lower()]) for n in names.split('/') if n.strip().lower() in GENRE_IDS]
    return ','.join(ids)


def item_type_and_id(container, index=None):
    prefix = list_prefix(container, index)
    dbtype = info(f'{prefix}.DBType')
    if dbtype in ('episode', 'season'):
        tmdb_id = info(f'{prefix}.Property(tvshow.tmdb_id)') or info(f'{prefix}.UniqueID(tmdb)')
        return 'tv', tmdb_id
    tmdb_id = info(f'{prefix}.UniqueID(tmdb)') or info(f'{prefix}.Property(tmdb_id)')
    return ('tv' if dbtype == 'tvshow' else 'movie'), tmdb_id


def open_details(container, index=None):
    item_type, tmdb_id = item_type_and_id(container, index)
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
    set_string(f'DetailGenres{page}', genre_ids(container, index))
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
        open_details(args[1], args[2] if len(args) > 2 else None)
    elif action == 'person' and len(args) > 1:
        open_person(args[1])


main()
