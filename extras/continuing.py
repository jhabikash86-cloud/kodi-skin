# -*- coding: utf-8 -*-
"""Continue Watching, as one row: films and episodes you are part-way through, and the next
episode of each show you are watching, newest first - as Apple TV's Up Next.

TMDb Helper has no list that mixes films and episodes, and a Kodi row with two lists froze
Kodi (see ATV_UpNextRow). So this builds the row itself: it reads TMDb Helper's films in
progress, episodes in progress and next episodes, orders them by when you last watched or
paused each title (TMDb Helper's own Trakt sync table), and writes the tiles to skin
strings the row draws (Home.xml, ATV_ContinueRow). Skin strings survive a restart, so the
row is there the moment Home opens and is brought up to date seconds later; and because
the row is rebuilt after each playback, what you just watched is at the front - a plain
list row kept the listing it opened with until Kodi restarted.

    import continuing; continuing.refresh()     # extras/prefetch.py, and after forget.py
"""
import datetime
import json
import re
import sqlite3

import xbmc
import xbmcvfs

PLUGIN = 'plugin://plugin.video.themoviedb.helper/?'
IN_PROGRESS = 'exclude_key=ResumeTime&exclude_value=0&exclude_operator=eq&nextpage=false'
FILMS = f'{PLUGIN}info=trakt_ondeck&tmdb_type=movie&{IN_PROGRESS}'
EPISODES = f'{PLUGIN}info=trakt_ondeck&tmdb_type=tv&{IN_PROGRESS}'
NEXT = f'{PLUGIN}info=trakt_nextepisodes&tmdb_type=tv&nextpage=false'
SYNC_DB = 'special://profile/addon_data/plugin.video.themoviedb.helper/database_07/ItemDetails.db'
PROPS = ['title', 'showtitle', 'season', 'episode', 'art', 'resume', 'uniqueid', 'year', 'file']
PREFIX = 'ATVCW'
SLOTS = 15                 # tiles in the row (Home.xml has as many static items)
RECENT_DAYS = 90           # older than this and it is not "continue", it is abandoned
HIDDEN = 'ATVCWHidden'     # skin string: kind:tmdb@when for each tile removed from the row
FIELDS = ('title', 'subtitle', 'art', 'percent', 'kind', 'tmdb', 'season', 'episode', 'path', 'resume')


def listing(path):
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Files.GetDirectory',
               'params': {'directory': path, 'media': 'video', 'properties': PROPS}}
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(request)))['result'].get('files') or []
    except (ValueError, KeyError, TypeError):
        return []


def recency():
    """id -> the latest of last watched and last paused, from TMDb Helper's Trakt sync."""
    try:
        db = sqlite3.connect(xbmcvfs.translatePath(SYNC_DB), timeout=5)
        rows = db.execute("SELECT id, last_watched_at, playback_paused_at FROM simplecache "
                          "WHERE id LIKE 'movie.%' OR id LIKE 'tv.%'").fetchall()
        db.close()
    except sqlite3.Error:
        return {}
    return {key: max(x for x in (watched, paused) if x) for key, watched, paused in rows if watched or paused}


def recent(when):
    if not when:
        return False
    try:   # not strptime: inside Kodi it can fail after its first use ('NoneType' not callable)
        then = datetime.datetime(*(int(x) for x in re.split(r'[-T:]', when[:19])))
    except (ValueError, TypeError):
        return True
    return (datetime.datetime.utcnow() - then).days <= RECENT_DAYS


def art(item):
    a = item.get('art') or {}
    return (a.get('landscape') or a.get('tvshow.landscape') or a.get('fanart') or a.get('tvshow.fanart')
            or a.get('thumb') or a.get('poster') or '')


def progress(item):
    r = item.get('resume') or {}
    position, total = float(r.get('position') or 0), float(r.get('total') or 0)
    return int(position), (int(position * 100 / total) if total else 0)


def build():
    when = recency()
    tiles = []
    for f in listing(FILMS):
        tmdb = (f.get('uniqueid') or {}).get('tmdb')
        resume, percent = progress(f)
        tiles.append({'kind': 'movie', 'tmdb': tmdb, 'title': f.get('label') or f.get('title') or '',
                      'subtitle': 'Movie' + (f'  ·  {f["year"]}' if f.get('year') else ''),
                      'art': art(f), 'percent': percent, 'resume': resume, 'path': f.get('file') or '',
                      'when': when.get(f'movie.{tmdb}'), 'season': '', 'episode': ''})
    in_progress = {}
    for f in listing(EPISODES):
        ids = f.get('uniqueid') or {}
        in_progress.setdefault(ids.get('tvshow.tmdb'), f)      # newest paused first
    seen = set()
    # A show's next episode is the one to play - the one in progress if there is one
    for f in listing(NEXT) + list(in_progress.values()):
        show = (f.get('uniqueid') or {}).get('tvshow.tmdb')
        if not show or show in seen:
            continue
        seen.add(show)
        paused = in_progress.get(show)
        if paused and (paused.get('season'), paused.get('episode')) == (f.get('season'), f.get('episode')):
            f = paused
        resume, percent = progress(f)
        tiles.append({'kind': 'episode', 'tmdb': show, 'title': f.get('showtitle') or f.get('label') or '',
                      'subtitle': f'Season {f.get("season")}  ·  Episode {f.get("episode")}',
                      'art': art(f), 'percent': percent, 'resume': resume, 'path': f.get('file') or '',
                      'when': when.get(f'tv.{show}'), 'season': str(f.get('season')), 'episode': str(f.get('episode'))})
    hidden = set(filter(None, xbmc.getInfoLabel(f'Skin.String({HIDDEN})').split('|')))
    tiles = [t for t in tiles if recent(t['when'])
             and f"{'tv' if t['kind'] == 'episode' else 'movie'}:{t['tmdb']}@{t['when']}" not in hidden]
    tiles.sort(key=lambda t: t['when'], reverse=True)
    return tiles[:SLOTS]


def publish(tiles):
    """Only what changed: each skin string set is a write of the skin's settings."""
    for slot in range(1, SLOTS + 1):
        tile = tiles[slot - 1] if slot <= len(tiles) else {}
        for field in FIELDS:
            value = str(tile.get(field, ''))
            name = f'{PREFIX}.{slot}.{field}'
            if xbmc.getInfoLabel(f'Skin.String({name})') != value:
                if value:
                    xbmc.executebuiltin(f'Skin.SetString({name},{quoted(value)})')
                else:
                    xbmc.executebuiltin(f'Skin.Reset({name})')


def quoted(text):
    """A builtin argument that may hold commas and brackets: in quotes, quotes escaped."""
    return '"%s"' % text.replace('\\', '\\\\').replace('"', '\\"')


def hide(kind, tmdb_id):
    """Take a title off the row until it is watched again: its entry names the last-watched
    time it had, and watching it moves that on."""
    for slot in range(1, SLOTS + 1):
        tile_kind = xbmc.getInfoLabel(f'Skin.String({PREFIX}.{slot}.kind)')
        if xbmc.getInfoLabel(f'Skin.String({PREFIX}.{slot}.tmdb)') == str(tmdb_id) and \
                ('tv' if tile_kind == 'episode' else 'movie') == kind:
            break
    else:
        return
    when = recency().get(f'{kind}.{tmdb_id}', '')
    entries = [e for e in xbmc.getInfoLabel(f'Skin.String({HIDDEN})').split('|') if e][-50:]
    entries.append(f'{kind}:{tmdb_id}@{when}')
    xbmc.executebuiltin(f'Skin.SetString({HIDDEN},{quoted("|".join(entries))})')
    refresh()


def refresh():
    tiles = build()
    if tiles or not xbmc.getInfoLabel(f'Skin.String({PREFIX}.1.title)'):
        publish(tiles)          # an empty answer from a failed fetch does not wipe the row
    xbmc.log(f'ATV continue: {len(tiles)} tiles - ' + ', '.join(t['title'] for t in tiles[:5]), xbmc.LOGINFO)
    return tiles
