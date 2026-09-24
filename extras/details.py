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


def set_strings(values):
    """Several skin strings at once: send them all, then wait once.

    Kodi applies builtins in the order they were sent, so waiting on every string in
    turn only multiplied the delay before a title page could open.
    """
    for name, value in values:
        if value:
            escaped = value.replace('\\', '\\\\').replace('"', '\\"')
            xbmc.executebuiltin(f'Skin.SetString({name},"{escaped}")')
        else:
            xbmc.executebuiltin(f'Skin.Reset({name})')
    for _ in range(100):
        if all(info(f'Skin.String({name})') == (value or '') for name, value in values):
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


def genre_ids(prefix):
    """Comma separated TMDb genre ids (= all of them) for the item."""
    names = info(f'{prefix}.Genre')
    ids = [str(GENRE_IDS[n.strip().lower()]) for n in names.split('/') if n.strip().lower() in GENRE_IDS]
    return ','.join(ids)


def language(prefix):
    """The title's own language, so recommendations can stay in it.

    A Rajinikanth film should suggest more Tamil cinema, not the global popularity
    list its genres would otherwise return.
    """
    return info(f'{prefix}.Property(original_language)')


# Formats that crowd a TV genre list without being what anyone means by a show like this
# one: soap, news, talk, reality, kids. The TV tab leaves them out for the same reason.
NOT_SERIALS = '10766,10763,10767,10764,10762'


def years_ago(years):
    import datetime
    return (datetime.date.today() - datetime.timedelta(days=int(years * 365.25))).isoformat()


def discover_filter(prefix, media, fallback_language=''):
    """The discover query for More Like This, as one string - sort order included.

    Built from the title's own genres and language, then held to a standard, because a
    genre list sorted by popularity alone is whatever has aired the longest: The
    Gentlemen got Monk, Psych and Rizzoli & Isles. Films stay popular but recent and
    well-voted; shows are sorted by rating over the last twelve years. English titles
    have far more votes to go on, so their floor is higher. A vote floor also drops
    unreleased titles, which have none.

    One string on purpose: as separate skin strings the container could be built before
    all of them had committed, and quietly fell back.
    """
    genres = genre_ids(prefix)
    if not genres:
        return 'similar'
    own = genres.split(',')
    # TMDb joins these with AND. Four genres matched almost nothing - Crystal Lake's
    # Mystery / Action / Drama / Comedy - so the first two, which TMDb lists as the main ones.
    genres = ','.join(own[:2])
    code = language(prefix) or fallback_language
    english = code in ('', 'en')
    parts = [f'with_genres={genres}&with_id=True']
    if code:
        parts.append(f'with_original_language={code}')
    if media == 'tv':
        # Never exclude a show's own format: a soap's More Like This is other soaps.
        excluded = ','.join(g for g in NOT_SERIALS.split(',') if g not in own)
        parts.append((f'without_genres={excluded}&' if excluded else '') + f'first_air_date.gte={years_ago(12)}'
                     f'&vote_count.gte={150 if english else 20}&sort_by=vote_average.desc')
    else:
        parts.append(f'primary_release_date.gte={years_ago(20)}'
                     f'&vote_count.gte={100 if english else 15}&sort_by=popularity.desc')
    return '&'.join(parts)


def row_came_back_empty(window, container, timeout=12):
    """True when the row finished loading with nothing in it."""
    xbmc.sleep(300)  # let the new path register before judging it
    for _ in range(timeout * 10):
        if xbmcgui.getCurrentWindowId() != window:
            return False
        if not xbmc.getCondVisibility(f'Container({container}).IsUpdating'):
            return not int(info(f'Container({container}).NumItems') or 0)
        xbmc.sleep(100)
    return False


def wait_for_details(window, tmdb_id, timeout=10):
    """True once the open title page's details listing is this title's.

    ActivateWindow is asynchronous, so first wait for the page to open at all. After
    that, give up if it is left, so a quick Back never has a stale script writing into
    a page that has already moved on.
    """
    for _ in range(40):
        if xbmcgui.getCurrentWindowId() == window:
            break
        xbmc.sleep(50)
    else:
        return False
    for _ in range(timeout * 20):
        if xbmcgui.getCurrentWindowId() != window:
            return False
        if (info('Container(9500).ListItem.UniqueID(tmdb)') == tmdb_id
                and not xbmc.getCondVisibility('Container(9500).IsUpdating')):
            return True
        xbmc.sleep(50)
    return False


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
    tile = list_prefix(container, index)
    # Everything the page needs before it can open on the right picture. The tile's own
    # art goes across too, so the page never opens on the last title's backdrop.
    set_strings([
        (f'DetailType{page}', item_type),
        (f'DetailLang{page}', language(tile)),
        (f'DetailFanart{page}', info(f'{tile}.Art(fanart)')),
        (f'DetailLogo{page}', info(f'{tile}.Art(clearlogo)')),
        (f'DetailTitle{page}', info(f'{tile}.Title') or info(f'{tile}.Label')),
        (f'DetailDiscover{page}', ''),  # More Like This waits for the details below
        (f'DetailNext{page}', ''),      # clear the previous title's episode first
        (f'DetailID{page}', tmdb_id),
    ])
    tile_language = language(tile)
    if on_page and page == current:  # deepest page: show the new title in place
        xbmc.executebuiltin('SetFocus(9601)')
    else:
        xbmc.executebuiltin(f'ActivateWindow({FIRST_PAGE + page})')
    window = FIRST_PAGE + page + 10000
    if item_type == 'tv':
        import play  # only shows need it; importing it for every film slowed every click
        # After the window is up: these are two Trakt list reads, and the page should not
        # wait on them. The Play button reads "Play" until this lands a moment later.
        season, episode, resume = play.next_episode(tmdb_id)
        verb = 'Resume' if resume else 'Play'
        set_string(f'DetailNext{page}', f'{verb} S{season} E{episode}')
    # The tile that was clicked can carry only its first genre - a Comedy / Horror /
    # Romance film arrived as "Comedy" and More Like This filled with children's films -
    # so the filter is built from the title's own details, once they are on the page.
    if wait_for_details(window, tmdb_id):
        set_string(f'DetailDiscover{page}', discover_filter('Container(9500).ListItem', item_type, tile_language))
        # A niche title can match nothing at this standard, which left an empty row.
        # Then TMDb's own "similar" list - broader, but never empty for a real title.
        if row_came_back_empty(window, 9630):
            set_string(f'DetailDiscover{page}', 'similar')


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
