# -*- coding: utf-8 -*-
"""Top 10 charts from what people actually watch: India first, then the world.

Trakt's and TMDb's charts are popularity across the world - neither says what is watched in
one country. Netflix publishes its weekly Top 10 for every country, real viewing, so a chart
here is built from that: India's list first, then the worldwide list (non-English titles, for
the Hindi and Tamil charts), then TMDb's most popular recent titles in that language, until
there are ten.

    Top 10 Movies in India / Shows in India    India's list as it stands
    Top 10 Hindi / Tamil Movies, Series        India's titles in that language, then the
                                               world's, then TMDb's popular ones

It only covers Netflix - Prime and JioHotstar publish nothing - but it is the one public
record of what India is watching. Titles are matched to TMDb through TMDb Helper's own
search (its language filter tells Hindi from Tamil), each match kept for good, so a week's
new entries are the only lookups. The tiles are skin strings, as Continue Watching's
(extras/continuing.py), so the rows are there the moment Home opens.

    import charts; charts.refresh()        # extras/prefetch.py, every few hours
"""
import json
import re
import time
import urllib.request
from urllib.parse import quote_plus

import xbmc
import xbmcvfs

INDIA = {'movie': 'https://www.netflix.com/tudum/top10/india',
         'tv': 'https://www.netflix.com/tudum/top10/india/tv'}
WORLD = 'https://www.netflix.com/tudum/top10/data/all-weeks-global.tsv'
WORLD_CATEGORY = {'movie': 'Films (Non-English)', 'tv': 'TV (Non-English)'}
PLUGIN = 'plugin://plugin.video.themoviedb.helper/?'
FOLDER = 'special://profile/addon_data/skin.appletv.minimal/'
CACHE = FOLDER + 'charts.json'
PREFIX = 'ATVTop'
SIZE = 10
FETCH_EVERY = 12 * 3600       # Netflix updates weekly; twice a day catches it within hours
RETRY_MISS = 7 * 86400        # a title that matched nothing is looked up again after a week
MATCHING = 2                  # raised when the matching rules change: older matches are redone
HEADERS = {'User-Agent': 'Mozilla/5.0 (ATV Minimal Kodi skin)'}
FIELDS = ('tmdb', 'type', 'title', 'poster', 'fanart')
SPOT = 'ATVSpot'               # Home's Spotlight: India's number one, a film one day, a show the next
SPOT_FIELDS = ('tmdb', 'type', 'title', 'kicker', 'fanart', 'logo', 'plot', 'year', 'rating', 'genre1', 'genre2')

# chart -> (media type, language or None for every language)
CHARTS = {
    'in_movie': ('movie', None), 'in_tv': ('tv', None),
    'hi_movie': ('movie', 'hi'), 'ta_movie': ('movie', 'ta'),
    'hi_tv': ('tv', 'hi'), 'ta_tv': ('tv', 'ta'),
}
# what fills a language chart after the viewing lists: TMDb's most popular recent titles
FILL = {
    'movie': 'info=discover&tmdb_type=movie&with_original_language={lang}&sort_by=popularity.desc'
             '&primary_release_date.gte={since}&vote_count.gte=5&with_id=True&hide_unaired=true',
    'tv': 'info=discover&tmdb_type=tv&with_original_language={lang}&sort_by=popularity.desc'
          '&first_air_date.gte={since}&without_genres=10766,10763,10767,10764,10762&with_id=True&hide_unaired=true',
}


def log(message):
    xbmc.log(f'ATV charts: {message}', xbmc.LOGINFO)


def fetch(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=timeout) as response:
        return response.read().decode('utf-8', 'replace')


def clean(title):
    """A Netflix title as TMDb names it: "Shaque: Trust No One: Season 1" is the show "Shaque:
    Trust No One"; "Raw: 2026 - September 21, 2026" is "Raw"."""
    title = re.sub(r'\s*:\s*(Season|Series|Part|Volume|Vol\.|Chapter|Limited Series|Book)\b.*$', '', title, flags=re.I)
    title = re.sub(r'\s*:\s*\d{4}\b.*$', '', title)
    return title.strip()


def india(kind):
    """India's Netflix Top 10 this week, titles in order, from its page on Netflix's site."""
    page = fetch(INDIA[kind])
    cells = re.findall(r'<td[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</td>', page, re.S)
    titles = []
    for cell in cells:
        text = re.sub(r'<[^>]+>', '', cell)
        text = re.sub(r'^\s*\d{1,2}', '', text)                      # the rank, printed in front
        text = text.replace('&amp;', '&').replace('&#39;', "'").replace('&quot;', '"').strip()
        if text:
            titles.append(clean(text))
    return titles[:SIZE]


def world():
    """The worldwide non-English Top 10 of the latest week, by kind."""
    rows = [line.split('\t') for line in fetch(WORLD, timeout=60).splitlines()[1:] if line]
    latest = max(row[0] for row in rows)
    found = {'movie': [], 'tv': []}
    for row in rows:
        for kind, category in WORLD_CATEGORY.items():
            if row[0] == latest and row[1] == category:
                found[kind].append((int(row[2]), clean(row[3])))
    return {kind: [t for _, t in sorted(items)] for kind, items in found.items()}, latest


def listing(query, properties=('title', 'art', 'uniqueid', 'year')):
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Files.GetDirectory',
               'params': {'directory': PLUGIN + query + '&nextpage=false', 'media': 'video',
                          'properties': list(properties)}}
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(request)))['result'].get('files') or []
    except (ValueError, KeyError, TypeError):
        return []


def tile(item, kind):
    art = item.get('art') or {}
    tmdb = (item.get('uniqueid') or {}).get('tmdb') or ''
    return {'tmdb': str(tmdb), 'type': kind, 'title': item.get('label') or item.get('title') or '',
            'poster': art.get('poster') or '', 'fanart': art.get('fanart') or art.get('landscape') or ''}


def same(a, b):
    a, b = (re.sub(r'[^a-z0-9]+', '', x.lower()) for x in (a, b))
    return bool(a) and (a == b or a.startswith(b) or b.startswith(a))


def match(title, kind, lang, known):
    """TMDb's title for a chart entry, or None - in that language only, when one is given.

    Released titles only. In a language, the name must be the chart's own: asked for Tamil,
    the Hindi "Gandhari" at number 7 in India found an unreleased Tamil film of the same name.
    """
    key = f'{kind}|{lang or "*"}|{title.lower()}'
    hit = known.get(key)
    if hit and hit.get('v') == MATCHING and (hit.get('tmdb') or time.time() - hit.get('at', 0) < RETRY_MISS):
        return hit if hit.get('tmdb') else None
    language = f'&filter_key=original_language&filter_value={lang}' if lang else ''
    found = None
    for query in dict.fromkeys([title, title.split(':')[0].strip()]):
        items = listing(f'info=search&tmdb_type={kind}&query={quote_plus(query)}{language}&hide_unaired=true')
        if lang:
            items = [i for i in items if same(i.get('label') or i.get('title') or '', query)]
        if items:
            found = tile(items[0], kind)
            break
    known[key] = dict(found or {}, at=time.time(), v=MATCHING)
    return found


def build(state, since):
    known = state.setdefault('known', {})
    lists = state['lists']
    charts = {}
    for chart, (kind, lang) in CHARTS.items():
        tiles, seen = [], set()

        def add(entry):
            if entry and entry.get('tmdb') and entry['tmdb'] not in seen and len(tiles) < SIZE:
                seen.add(entry['tmdb'])
                tiles.append(entry)

        for title in lists.get('india_' + kind, []):
            add(match(title, kind, lang, known))
        if lang:
            for title in lists.get('world_' + kind, []):
                if len(tiles) >= SIZE:
                    break
                add(match(title, kind, lang, known))
            if len(tiles) < SIZE:
                for item in listing(FILL[kind].format(lang=lang, since=since)):
                    add(tile(item, kind))
        charts[chart] = tiles
        log(f'{chart}: ' + ', '.join(t['title'] for t in tiles[:5]))
    return charts


def spotlight(charts):
    """India's number one this week, with what the Spotlight card shows of it."""
    kind = 'movie' if time.localtime().tm_yday % 2 == 0 else 'tv'
    pick = (charts.get('in_' + kind) or charts.get('in_movie') or [None])[0]
    if not pick:
        return {}
    items = listing(f'info=details&tmdb_type={pick["type"]}&tmdb_id={pick["tmdb"]}',
                    ('title', 'art', 'plot', 'genre', 'year', 'rating'))
    if not items:
        return {}
    item, art = items[0], items[0].get('art') or {}
    genres = item.get('genre') or []
    return {'tmdb': pick['tmdb'], 'type': pick['type'], 'title': item.get('label') or pick['title'],
            'kicker': '#1 IN INDIA THIS WEEK', 'fanart': art.get('fanart') or pick['fanart'],
            'logo': art.get('clearlogo') or '', 'plot': (item.get('plot') or '').replace('\n', ' '),
            'year': str(item.get('year') or ''), 'rating': f'{item["rating"]:.1f}' if item.get('rating') else '',
            'genre1': genres[0] if genres else '', 'genre2': genres[1] if len(genres) > 1 else ''}


def set_string(name, value):
    if xbmc.getInfoLabel(f'Skin.String({name})') != value:
        if value:
            xbmc.executebuiltin(f'Skin.SetString({name},"%s")' % value.replace('"', '\\"'))
        else:
            xbmc.executebuiltin(f'Skin.Reset({name})')


def publish(charts):
    """Only what changed: each skin string set is a write of the skin's settings."""
    for chart, tiles in charts.items():
        if not tiles:
            continue                 # a failed build keeps the row as it was
        for slot in range(1, SIZE + 1):
            entry = tiles[slot - 1] if slot <= len(tiles) else {}
            for field in FIELDS:
                name, value = f'{PREFIX}.{chart}.{slot}.{field}', str(entry.get(field, ''))
                if xbmc.getInfoLabel(f'Skin.String({name})') != value:
                    if value:
                        xbmc.executebuiltin(f'Skin.SetString({name},"%s")' % value.replace('"', '\\"'))
                    else:
                        xbmc.executebuiltin(f'Skin.Reset({name})')


def load():
    try:
        f = xbmcvfs.File(CACHE)
        try:
            return json.loads(f.read() or '{}')
        finally:
            f.close()
    except ValueError:
        return {}


def save(state):
    xbmcvfs.mkdirs(FOLDER)
    f = xbmcvfs.File(CACHE, 'w')
    try:
        f.write(json.dumps(state))
    finally:
        f.close()


def refresh(force=False):
    state = load()
    if force or time.time() - state.get('fetched', 0) > FETCH_EVERY or not state.get('lists'):
        lists = dict(state.get('lists') or {})
        try:
            for kind in INDIA:
                titles = india(kind)
                if titles:
                    lists['india_' + kind] = titles
            worldwide, week = world()
            for kind, titles in worldwide.items():
                if titles:
                    lists['world_' + kind] = titles
            state.update(lists=lists, fetched=time.time(), week=week)
            log(f'fetched, week of {week}: India {len(lists.get("india_movie", []))} films, '
                f'{len(lists.get("india_tv", []))} shows')
        except Exception as error:      # offline, or Netflix changed its pages: keep what we had
            log(f'could not fetch the charts ({error})')
            if not state.get('lists'):
                return
    import dates
    since = dates.values()['d540']
    charts = build(state, since)
    save(state)
    publish(charts)
    spot = spotlight(charts)
    if spot:
        for field in SPOT_FIELDS:
            set_string(f'{SPOT}.{field}', spot.get(field, ''))
        log(f'spotlight: {spot["title"]}')
    return charts


if __name__ == '__main__':
    refresh(force=True)
