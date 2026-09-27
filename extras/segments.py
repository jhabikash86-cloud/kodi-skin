# -*- coding: utf-8 -*-
"""Where an episode's intro, recap and credits are, from TheIntroDB (theintrodb.org): a free,
community-timed database keyed by TMDb id, season and episode, read without an account.

    import segments; segments.fetch(tmdb_id, season, episode)
    -> {'skips': [('Intro', 312.1, 340.3), ...], 'credits': 2843.0}     (seconds; {} if unknown)

Used by extras/upnext.py for Skip Intro / Skip Recap, and to offer the next episode as the
credits start rather than a fixed time before the end.
"""
import json
import urllib.request
from urllib.parse import urlencode

import xbmc

API = 'https://api.theintrodb.org/v3/media?'
TIMEOUT = 6
SKIPPABLE = (('recap', 'Recap'), ('intro', 'Intro'))
SHORTEST = 8          # seconds: a "skip" shorter than this is not worth a button


def fetch(tmdb_id, season, episode):
    url = API + urlencode({'tmdb_id': tmdb_id, 'season': season, 'episode': episode})
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'ATV Minimal (Kodi skin)'})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception as error:     # not in the database (404), offline, slow: no skips
        xbmc.log(f'ATV segments: none for {tmdb_id} S{season}E{episode} ({error})', xbmc.LOGINFO)
        return {}
    skips = []
    for key, label in SKIPPABLE:
        for part in data.get(key) or []:
            start, end = (part.get('start_ms') or 0) / 1000.0, part.get('end_ms')
            if end is not None and end / 1000.0 - start >= SHORTEST:
                skips.append((label, start, end / 1000.0))
    credits = [p.get('start_ms') for p in data.get('credits') or [] if p.get('start_ms')]
    found = {'skips': sorted(skips, key=lambda s: s[1]), 'credits': min(credits) / 1000.0 if credits else None}
    xbmc.log(f'ATV segments: {tmdb_id} S{season}E{episode} {found}', xbmc.LOGINFO)
    return found
