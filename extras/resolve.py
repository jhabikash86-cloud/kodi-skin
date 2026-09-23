# -*- coding: utf-8 -*-
"""Pick the best release of the right film from your own debrid cache, and play it.

POV decides what to play from whatever its providers hand back, and several of those
providers return links already resolved through somebody else's debrid account. The
result is that your own Real-Debrid cache is never consulted: Kabali came back as a
720p from a shared instance while your account held a 1080p AMZN WEB-DL, and Animal
played the French "Le Regne Animal" in 4K instead of the Hindi film.

This asks Torrentio directly, with your own debrid keys, for the releases that account
has cached - they come back as playable links - then ranks them and tries them in turn:

    best quality -> if it will not play, the next best -> and so on

Three filters do the real work:

  * the right film      - "le.regne.animal.2023" is not "animal" (see is_wrong_film)
  * not an extra        - Kabali's only two 4K entries on this account are teasers
  * a plausible size    - a feature film is not 80MB

Nothing here prints or stores a token; the keys are read from POV's settings, used to
build a request, and forgotten.

    RunScript(special://skin/extras/resolve.py,movie,<tmdb_id>)
    RunScript(special://skin/extras/resolve.py,tv,<tmdb_id>,<season>,<episode>)
"""
import json
import re
import sys

import xbmc
import xbmcaddon
import xbmcgui

PLUGIN = 'plugin://plugin.video.themoviedb.helper/?'
TORRENTIO = 'https://torrentio.strem.fun'
POV_ADDON = 'plugin.video.pov'

ATTEMPTS = 6          # how many releases to try before giving up
START_TIMEOUT = 40    # seconds to wait for one release to start
SETTLE = 4            # a dead link opens and stops again inside this
MIN_GB = 0.4          # below this it is a teaser, a sample or a trailer
QUALITY_ORDER = ('4K', '1080p', '720p', 'SD')

EXTRAS = re.compile(r'\b(teaser|trailer|sample|promo|making|behind|deleted|featurette)\b', re.I)
SIZE = re.compile(r'([\d.]+)\s*(GB|MB)', re.I)
YEAR = re.compile(r'\b(19|20)\d{2}\b')
SITEISH = re.compile(r'\d|^www$|^(?:com|net|org|info|world|me|to|cc|io|tv)$')


def jsonrpc(method, **params):
    request = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
    try:
        return json.loads(xbmc.executeJSONRPC(request)).get('result') or {}
    except ValueError:
        return {}


def details(kind, tmdb_id):
    """(imdb id, title) for a title, straight from TMDb Helper."""
    result = jsonrpc(
        'Files.GetDirectory',
        directory=f'{PLUGIN}info=details&tmdb_type={kind}&tmdb_id={tmdb_id}&nextpage=false',
        media='video', properties=['title', 'uniqueid'])
    for item in result.get('files') or []:
        ids = item.get('uniqueid') or {}
        imdb = ids.get('imdb') or ids.get('tvshow.imdb')
        if imdb and imdb != 'None':
            return imdb, item.get('label') or ''
    return '', ''


def debrid_keys():
    """Your debrid tokens, in the order Torrentio names them."""
    try:
        pov = xbmcaddon.Addon(POV_ADDON)
    except Exception:
        return []
    keys = []
    for setting, service in (('rd.token', 'realdebrid'), ('ad.token', 'alldebrid')):
        token = pov.getSetting(setting)
        if token:
            keys.append((service, token))
    return keys


def fetch(url):
    import urllib.request
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode()).get('streams') or []
    except Exception:
        return []


def normalise(text):
    return re.sub(r'[^a-z0-9]+', '.', (text or '').lower()).strip('.')


def is_wrong_film(name, title):
    """True when the release name reads like a different film. See extras/play.py."""
    name, wanted = normalise(name), normalise(title)
    if not name or not wanted:
        return False
    position = name.find(wanted)
    if position < 0:
        return True
    year = YEAR.search(name)
    if year and not name[:year.start()].strip('.').endswith(wanted):
        return True
    extra = [t for t in name[:position].split('.') if t and not SITEISH.search(t) and len(t) > 1]
    return len(extra) > 1


def size_gb(text):
    match = SIZE.search(text or '')
    if not match:
        return 0.0
    value = float(match.group(1))
    return value / 1024 if match.group(2).upper() == 'MB' else value


def quality_of(text):
    lowered = (text or '').lower()
    if any(tag in lowered for tag in ('2160', '4k', 'uhd')):
        return '4K'
    if '1080' in lowered:
        return '1080p'
    if '720' in lowered:
        return '720p'
    return 'SD'


def candidates(imdb, title, season=None, episode=None):
    """Every cached release of this title, best first."""
    path = (f'/stream/series/{imdb}:{season}:{episode}.json' if season
            else f'/stream/movie/{imdb}.json')
    found, seen = [], set()
    for service, token in debrid_keys():
        for stream in fetch(f'{TORRENTIO}/{service}={token}{path}'):
            url = stream.get('url') or ''
            if not url.startswith('http'):
                continue                      # not cached: nothing to play yet
            name = (stream.get('title') or stream.get('name') or '').replace('\n', ' ')
            headline = name.split('👤')[0].strip()
            if EXTRAS.search(headline):
                continue                      # a teaser is not the film
            gigabytes = size_gb(name)
            if gigabytes and gigabytes < MIN_GB:
                continue
            if season is None and is_wrong_film(headline, title):
                continue
            key = headline.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append({'url': url, 'name': headline,
                          'quality': quality_of(name), 'size': gigabytes})
    found.sort(key=lambda s: (QUALITY_ORDER.index(s['quality']), -s['size']))
    return found


def plays(url):
    """Start a release and say whether it actually runs."""
    player = xbmc.Player()
    xbmc.executebuiltin(f'PlayMedia({url})')
    for _ in range(START_TIMEOUT * 4):
        if player.isPlayingVideo():
            break
        xbmc.sleep(250)
    else:
        return False
    xbmc.sleep(SETTLE * 1000)               # a dead link opens then stops again
    try:
        return player.isPlayingVideo()
    except RuntimeError:
        return False


def resolve(kind, tmdb_id, season=None, episode=None):
    imdb, title = details(kind, tmdb_id)
    if not imdb:
        return False
    progress = xbmcgui.DialogProgressBG()
    progress.create('Finding the best copy', title)
    try:
        ranked = candidates(imdb, title, season, episode)
        if not ranked:
            return False
        for index, stream in enumerate(ranked[:ATTEMPTS], 1):
            progress.update(int(index / min(len(ranked), ATTEMPTS) * 100),
                            message=f"{stream['quality']}  {stream['name'][:48]}")
            if plays(stream['url']):
                return True
        return False
    finally:
        progress.close()


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        return
    kind, tmdb_id = args[0], args[1]
    season = args[2] if len(args) > 2 else None
    episode = args[3] if len(args) > 3 else None
    if not resolve(kind, tmdb_id, season, episode):
        xbmcgui.Dialog().notification(
            'Nothing playable found', 'Try Sources for more releases',
            xbmcgui.NOTIFICATION_INFO, 4000)


if __name__ == '__main__':
    main()
