# -*- coding: utf-8 -*-
"""Fetch what you are about to open, before you open it.

Every row and title page is a TMDb Helper listing. TMDb Helper caches what it fetches, and
a cached listing comes back in about 0.3s against 1.4s for one it has to fetch - measured
on this skin, per row. The first visit of the day to Movies or TV pays that for ten rows at
once, and every title page pays it for its details. This does the fetching early:

  * at startup, every row of the Movies and TV pages, one after another in the background,
    so the first visit to either is as quick as the second;
  * the titles in the Home hero, which are the ones most often opened;
  * whichever title you rest on for a moment, anywhere, so that its page - details and
    "You May Also Like" - is already cached when you select it.

Kodi lets a skin register no service, so this is a loop started by Home's <onload>, like
extras/trailer.py. One runs at a time; it lasts until Kodi exits.

    RunScript(special://skin/extras/prefetch.py)
"""
import json
import re
import threading
import time

import xbmc
import xbmcgui

from waiting import Monitor  # same folder; Kodi puts a RunScript's directory on sys.path
import xbmcvfs

import dates  # same folder; Kodi puts a RunScript's directory on sys.path

PLUGIN = 'plugin://plugin.video.themoviedb.helper/?'
HOME = xbmcgui.Window(10000)
RUNNING = 'ATVPrefetchWatcher'
PAGES = ('Custom_1140_Movies.xml', 'Custom_1141_TVShows.xml')
POLL_MS = 200
DWELL = 0.35         # seconds on one title before its page is worth fetching - details
                     # take ~1.4s to fetch, so the earlier this starts the more of it is done
REWARM = 3 * 3600    # TMDb Helper's list caches expire; walk the rows again this often
STARTUP_DELAY = 8    # let Home load its own rows first - they are what is on screen
if xbmc.getCondVisibility('System.Platform.UWP'):
    STARTUP_DELAY = 25   # the Xbox takes longer over Home, and this would compete with it
REMEMBERED = 200     # titles fetched recently, so moving back and forth costs nothing
DATES_EVERY = 60     # seconds between checks that the date windows are still today's



def jsonrpc(method, **params):
    request = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
    try:
        return json.loads(xbmc.executeJSONRPC(request)).get('result') or {}
    except ValueError:
        return {}


def fetch(path):
    """Ask for a listing only so that TMDb Helper caches it."""
    jsonrpc('Files.GetDirectory', directory=path, media='video', properties=['title'])


def page_rows():
    """Every fixed row path on the Movies and TV pages, read from the pages themselves."""
    paths = []
    for name in PAGES:
        try:
            with xbmcvfs.File(f'special://skin/xml/{name}') as f:
                xml = f.read()
        except Exception:
            continue
        for match in re.finditer(r'(plugin://plugin\.video\.themoviedb\.helper/\?[^"<]+)', xml):
            path = dates.resolve(match.group(1).replace('&amp;', '&'))
            if '$INFO' not in path and '$VAR' not in path and path not in paths:
                paths.append(path)
    return paths


def title_paths(kind, tmdb_id):
    """What a title page asks for first: its details, and "You May Also Like"."""
    return [f'{PLUGIN}info=details&tmdb_type={kind}&tmdb_id={tmdb_id}&nextpage=false',
            f'{PLUGIN}info=recommendations&tmdb_type={kind}&tmdb_id={tmdb_id}&hide_unaired=true&nextpage=false']


def focused_title():
    """(kind, tmdb id) of the focused item, or None when it is not a title."""
    dbtype = xbmc.getInfoLabel('ListItem.DBType')
    if dbtype in ('episode', 'season'):
        tmdb_id = xbmc.getInfoLabel('ListItem.Property(tvshow.tmdb_id)')
        return ('tv', tmdb_id) if tmdb_id else None
    if dbtype not in ('movie', 'tvshow'):
        return None
    tmdb_id = xbmc.getInfoLabel('ListItem.UniqueID(tmdb)')
    return ('tv' if dbtype == 'tvshow' else 'movie', tmdb_id) if tmdb_id else None


class Fetcher:
    """One background worker, so fetching never competes with itself or blocks the loop."""

    def __init__(self, monitor):
        self.monitor = monitor
        self.queue = []
        self.resting = []   # the title being rested on; replaced, never queued up
        self.lock = threading.Lock()
        self.worker = threading.Thread(target=self.run, daemon=True)
        self.worker.start()

    def add(self, paths):
        with self.lock:
            self.queue += [p for p in paths if p not in self.queue]

    def rest_on(self, paths):
        """The title under the cursor now. Only the latest matters: a title scrolled past
        a second ago is not about to be opened, so it is dropped rather than queued."""
        with self.lock:
            self.resting = list(paths)

    def run(self):
        while not self.monitor.stopping():
            with self.lock:
                if self.resting:
                    path = self.resting.pop(0)      # ahead of the background walk
                else:
                    path = self.queue.pop(0) if self.queue else None
            if path is None:
                if self.monitor.stopping(0.2):
                    return
                continue
            fetch(path)



HERO = 'Container(40).ListItemAbsolute(0)'
FIRST_PAINT = {'hero': 40, 'continue watching': 50, 'continue watching films': 51, 'top 10 movies': 6052}


def quoted(text):
    """A builtin argument that may hold commas and brackets: in quotes, quotes escaped."""
    return '"%s"' % (text or '').replace('\\', '\\\\').replace('"', '\\"')


def save_hero():
    """Keep the hero's first item for next time (skin strings survive a restart), so Home
    opens on its picture while the list is still loading."""
    tmdb_id = xbmc.getInfoLabel(f'{HERO}.UniqueID(tmdb)')
    if not tmdb_id or tmdb_id == xbmc.getInfoLabel('Skin.String(ATVHero.id)'):
        return
    info = lambda label: xbmc.getInfoLabel(f'{HERO}.{label}')
    meta = 'Movie' + ''.join(f'  ·  {v}' for v in (info('Year'), info('Genre')) if v)
    if info('Rating'):
        meta += f'  ·  ★ {info("Rating")}'
    for name, value in (('fanart', info('Art(fanart)')), ('clearlogo', info('Art(clearlogo)')),
                        ('title', info('Title')), ('meta', meta), ('plot', info('Plot')),
                        ('id', tmdb_id)):
        xbmc.executebuiltin(f'Skin.SetString(ATVHero.{name},{quoted(value)})')


def hero_titles():
    titles = []
    for index in range(int(xbmc.getInfoLabel('Container(40).NumItems') or 0)):
        tmdb_id = xbmc.getInfoLabel(f'Container(40).ListItemAbsolute({index}).UniqueID(tmdb)')
        if tmdb_id:
            titles.append(('movie', tmdb_id))
    return titles


def watch():
    if HOME.getProperty(RUNNING) == '1':
        return
    HOME.setProperty(RUNNING, '1')
    monitor = Monitor()
    fetcher = Fetcher(monitor)
    fetched = []                  # recently fetched titles, oldest first
    warmed = time.time() - REWARM + STARTUP_DELAY  # first walk a few seconds from now
    resting_on, since = None, 0.0
    ordered = 0.0
    started, painted = time.time(), {}   # first paint of Home after a start, for the log
    try:
        while not monitor.stopping():
            if len(painted) < len(FIRST_PAINT) and time.time() - started < 30:
                for name, container in FIRST_PAINT.items():
                    if name not in painted and xbmc.getInfoLabel(f'Container({container}).NumItems') not in ('', '0'):
                        painted[name] = time.time() - started
                        xbmc.log(f'ATV timing: {name} filled {painted[name]:.1f}s after Home opened', xbmc.LOGINFO)
            save_hero()

            if time.time() - ordered > DATES_EVERY:
                ordered = time.time()
                dates.refresh()        # past midnight, the date windows move on

            if time.time() - warmed > REWARM:
                warmed = time.time()
                fetcher.add(page_rows())
                for kind, tmdb_id in hero_titles():
                    fetcher.add(title_paths(kind, tmdb_id))

            title = focused_title()
            if title != resting_on:
                resting_on, since = title, time.time()
            elif title and title not in fetched and time.time() - since >= DWELL:
                fetcher.rest_on(title_paths(*title))
                fetched.append(title)
                del fetched[:-REMEMBERED]

            if monitor.stopping(POLL_MS / 1000.0):
                break
    finally:
        HOME.clearProperty(RUNNING)
        fetcher.worker.join(2)   # a fetch in flight ends quickly; do not leave it behind


if __name__ == '__main__':
    watch()
