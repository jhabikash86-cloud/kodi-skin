# -*- coding: utf-8 -*-
"""Where an episode's intro, recap and credits are, from two free community databases:
TheIntroDB (theintrodb.org, by TMDb id) and IntroDB (introdb.app, by IMDb id). Neither
needs an account. The first is asked first; the second fills in whatever it lacks - it had
Furious, which the first did not.

    import segments; segments.fetch(tmdb_id, season, episode)
    -> {'skips': [('Recap', 0.0, 109.0), ('Intro', 312.1, 340.3)],
        'credits': 3197.0, 'post_credits': False}                  (seconds; {} if unknown)

Used by extras/upnext.py for Skip Intro / Skip Recap, and to offer the next episode as the
credits start rather than a fixed time before the end - unless there is a scene after them.
Episodes neither database knows fall back to the file's own chapter names (upnext.py).
"""
import json
import urllib.request
from urllib.parse import urlencode

import xbmc

THEINTRODB = 'https://api.theintrodb.org/v3/media?'
INTRODB = 'https://api.introdb.app/segments?'
TIMEOUT = 6
SHORTEST = 8          # seconds: a "skip" shorter than this is not worth a button
HEADERS = {'User-Agent': 'ATV Minimal (Kodi skin)'}   # both refuse Python's default agent


def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=TIMEOUT) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as error:     # not in the database (404), offline, slow
        return {'error': str(error)}


def show_imdb(tmdb_id):
    """The show's IMDb id, from TMDb Helper's details (cached after the title page)."""
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Files.GetDirectory', 'params': {
        'directory': f'plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=tv&tmdb_id={tmdb_id}&nextpage=false',
        'media': 'video', 'properties': ['uniqueid']}}
    try:
        files = json.loads(xbmc.executeJSONRPC(json.dumps(request)))['result'].get('files') or []
        return (files[0].get('uniqueid') or {}).get('imdb', '') if files else ''
    except (ValueError, KeyError, TypeError):
        return ''


def from_theintrodb(tmdb_id, season, episode):
    data = get(THEINTRODB + urlencode({'tmdb_id': tmdb_id, 'season': season, 'episode': episode}))
    found = {'skips': [], 'credits': None}
    for key, label in (('recap', 'Recap'), ('intro', 'Intro')):
        for part in data.get(key) or []:
            start, end = (part.get('start_ms') or 0) / 1000.0, part.get('end_ms')
            if end is not None:
                found['skips'].append((label, start, end / 1000.0))
    credits = [p.get('start_ms') for p in data.get('credits') or [] if p.get('start_ms')]
    if credits:
        found['credits'] = min(credits) / 1000.0
    return found


def from_introdb(imdb_id, season, episode):
    found = {'skips': [], 'credits': None, 'post_credits': False}
    if not imdb_id:
        return found
    data = get(INTRODB + urlencode({'imdb_id': imdb_id, 'season': season, 'episode': episode}))
    for key, label in (('recap', 'Recap'), ('intro', 'Intro')):
        part = data.get(key)
        if part and part.get('end_sec') is not None:
            found['skips'].append((label, float(part.get('start_sec') or 0), float(part['end_sec'])))
    outro = data.get('outro')
    if outro and outro.get('start_sec'):
        found['credits'] = float(outro['start_sec'])
    found['post_credits'] = bool(data.get('post_credits'))
    return found


def fetch(tmdb_id, season, episode):
    first = from_theintrodb(tmdb_id, season, episode)
    second = {}
    if not first['skips'] or first['credits'] is None:
        second = from_introdb(show_imdb(tmdb_id), season, episode)
    have = {label for label, _, _ in first['skips']}
    skips = first['skips'] + [s for s in second.get('skips', []) if s[0] not in have]
    skips = sorted((s for s in skips if s[2] - s[1] >= SHORTEST), key=lambda s: s[1])
    found = {'skips': skips,
             'credits': first['credits'] if first['credits'] is not None else second.get('credits'),
             'post_credits': second.get('post_credits', False)}
    xbmc.log(f'ATV segments: {tmdb_id} S{season}E{episode} {found}', xbmc.LOGINFO)
    return found if skips or found['credits'] else {}
