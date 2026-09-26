# -*- coding: utf-8 -*-
"""Set up the add-ons this skin works with, the way they were tuned on the first install.

A new device - the Xbox - otherwise needs a page of settings copied by hand before Play
opens Umbrella's source list, subtitles come in English, or pages load at all. This runs
at every start (Startup.xml), costs nothing once done, and for each add-on found:

  * TMDb Helper: the Umbrella players, Play set to open Umbrella's source list, and
    lighter posters on the Xbox
  * Umbrella: scraper timeout, early stop at 10 4K results, subtitles, resume, Trakt, the
    release filters, and Magneto as its external scraper
  * Magneto: the providers switched on as on the Mac
  * YouTube: its local server reachable, which the trailers need
  * Kodi: English subtitles, add-on updates notify only; advancedsettings.xml if none

Each add-on's settings are applied once, then left alone - change them afterwards and
they stay changed. Installing an add-on later is fine: it is set up at the next start.
Signing in (Trakt, TMDb, debrid) is yours to do; nothing here touches an account.

It also applies three fixes to TMDb Helper's shared module whenever it is found without
them - so an update of it is fixed again at the next start: IPv4 only and the lock crash
(README, "Why pages went blank"), and not caching a failed list, which left a row empty for
six hours; failed lists already cached are cleared.

    RunScript(special://skin/extras/setup.py)
"""
import json

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

SKIN = 'special://skin/extras/'
XBOX = xbmc.getCondVisibility('System.Platform.UWP')
STATE = 'special://profile/addon_data/skin.appletv.minimal/setup.json'
VERSION = 3   # raise to apply a changed list below once more

KODI = {
    'locale.subtitlelanguage': 'English',
    'general.addonupdates': 1,   # notify, don't install: an update can undo the IPv4 fix
}
if XBOX:
    # Apple TV's "Match Frame Rate": a film plays at its own 24 frames a second, not pulled
    # up to the TV's 60 with an uneven 3:2 cadence (judder on pans). Needs "Allow 24 Hz" in
    # the Xbox's video modes; the TV blanks for a moment as it switches.
    KODI['videoplayer.adjustrefreshrate'] = 2   # on start and stop of playback
ADDONS = {
    'plugin.video.themoviedb.helper': {
        # Original-size posters (2000x3000) look best on the Mac; on the Xbox each one is a
        # multi-megabyte download to decode and shrink, so there "Highest": w780 posters,
        # still sharper than the 300-450px a poster is drawn at, and original backdrops.
        'artwork_quality': 0 if XBOX else 4,
        'default_player_movies': 'umbrella.select.json play_movie',
        'default_player_episodes': 'umbrella.select.json play_episode',
        'combined_players': False,
        'bundled_players': False,
    },
    'plugin.video.umbrella': {
        'scrapers.timeout': 20,
        'preemptive.termination.movie': True,
        'preemptive.limit.movie': 10,
        'preemptive.res.movie': 0,
        'preemptive.termination.tv': True,
        'preemptive.limit.tv': 10,
        'preemptive.res.tv': 0,
        'sources.sort.order': 1,
        'source.prioritize.dolbyvisionfirst': True,
        'remove.cam.sources': True,
        'remove.sd.sources': True,
        'bookmarks.auto': True,
        'subtitles': True,
        'subtitles.notification': False,
        'indicators.alt': 1,
        'indicators': 'Trakt',
        'scrobble': 'Trakt',
        'scrobble.source': 1,
        # which releases are listed - as on the Mac
        'torrent.remove.uncached': False,
        'terminate.onCloud.sources': False,
        'rd_cloud.enabled': True,
        'remove.mp4': True,
        'remove.mpeg': True,
        'remove.wmv': True,
        'remove.audio.aac': True,
        'remove.audio.mp3': True,
        'dev.disable.season.filter': True,
        'dev.disable.show.filter': True,
    },
    # The scraper behind Umbrella's sources on the Mac. Umbrella takes one external scraper;
    # without it, it lists far fewer releases, and new shows (Furious) found none on the Xbox.
    'script.module.magneto': {
        'scraping_timeout': 30,
        'provider.piratebay': True,
        'provider.comet': True,
        'comet.url': 2,
        'provider.mediafusion': True,
        'mediafusion.url': 1,
        'provider.torrentio': True,
        'provider.torz': True,
        'provider.aiostreams': True,
        'aiostreams_instance': 4,
        'results.list_format': 1,
        'highlight.type': 1,
    },
    'plugin.video.youtube': {
        'kodion.http.listen': '0.0.0.0',
    },
}
# Umbrella's external scraper, set only once the scraper itself is installed - pointing
# Umbrella at a module that is missing breaks its source search
LINKS = {
    ('plugin.video.umbrella', 'script.module.magneto'): {
        'provider.external.enabled': True,
        'external_provider.module': 'script.module.magneto',
        'external_provider.name': 'magneto',   # the module Umbrella imports; the id alone is not enough
    },
}
PLAYERS = ('umbrella.select.json', 'umbrella.autoplay.json')
PLAYERS_DIR = 'special://profile/addon_data/plugin.video.themoviedb.helper/players/'
ADVANCED = 'special://profile/advancedsettings.xml'

MODULE = 'special://home/addons/script.module.jurialmunkey/resources/modules/jurialmunkey/'
IPV4 = (
    '            # skin.appletv.minimal: IPv4 only. From this network TMDb\'s API cannot be reached\n'
    '            # over IPv6 - every attempt times out - and urllib3 tries IPv6 first, so each\n'
    '            # uncached request stalled until its timeout while holding TMDb Helper\'s lock on\n'
    '            # that title. Every API TMDb Helper uses answers over IPv4.\n'
    '            try:\n'
    '                import urllib3.util.connection\n'
    '                urllib3.util.connection.HAS_IPV6 = False\n'
    '            except Exception:\n'
    '                pass\n'
)
CACHE_LINE = '            return self.set_cache(my_object, cache_name, cache_days, force=cache_force, fallback=cache_fallback)\n'
FIXES = {
    # file: (already fixed if this is in it, the line to find, what goes there instead)
    'bcache.py': ('skin.appletv.minimal: a list',
                  CACHE_LINE,
                  '            # skin.appletv.minimal: a list with no items and no pages is a request that\n'
                  '            # failed (TMDb answers with at least one page); cached, it kept a row empty\n'
                  '            # for six hours\n'
                  "            if isinstance(my_object, dict) and 'items' in my_object and not my_object.get('items') and not my_object.get('pages'):\n"
                  '                return my_object\n'
                  + CACHE_LINE),
    'reqapi.py': ('HAS_IPV6 = False',
                  '            self._session = self.requests.Session()\n',
                  IPV4 + '            self._session = self.requests.Session()\n'),
    'locker.py': ('if kodi_log is not None',
                  '        self._kodi_log = kodi_log\n',
                  '        if kodi_log is not None:  # skin.appletv.minimal: left unset, the property below makes a logger;\n'
                  '            self._kodi_log = kodi_log  # set to None it returned None, and a lock timeout crashed the caller\n'),
}


def log(message):
    xbmc.log(f'ATV setup: {message}', xbmc.LOGINFO)


def installed(addon_id):
    return xbmc.getCondVisibility(f'System.HasAddon({addon_id})')


def read(path):
    f = xbmcvfs.File(path)
    try:
        return f.read()
    finally:
        f.close()


def write(path, text):
    f = xbmcvfs.File(path, 'w')
    try:
        return f.write(text)
    finally:
        f.close()


def load_state():
    try:
        return json.loads(read(STATE) or '{}')
    except ValueError:
        return {}


def save_state(state):
    xbmcvfs.mkdirs('special://profile/addon_data/skin.appletv.minimal/')
    write(STATE, json.dumps(state))


def set_value(addon, key, value):
    """Typed where the add-on declares a type, as text where it does not."""
    try:
        if isinstance(value, bool):
            ok = addon.setSettingBool(key, value)
        elif isinstance(value, int):
            ok = addon.setSettingInt(key, value)
        else:
            ok = addon.setSettingString(key, value)
        if ok is not False:
            return
    except (TypeError, RuntimeError):
        pass
    addon.setSetting(key, str(value).lower() if isinstance(value, bool) else str(value))


def set_kodi(setting, value):
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.SetSettingValue',
               'params': {'setting': setting, 'value': value}}
    xbmc.executeJSONRPC(json.dumps(request))


def copy_players():
    if not installed('plugin.video.themoviedb.helper'):
        return
    xbmcvfs.mkdirs(PLAYERS_DIR)
    for name in PLAYERS:
        if not xbmcvfs.exists(PLAYERS_DIR + name):
            xbmcvfs.copy(SKIN + 'players/' + name, PLAYERS_DIR + name)
            log(f'added player {name}')


def fix_module():
    """The IPv4 and lock fixes, each only where its line is found exactly as expected."""
    if not installed('script.module.jurialmunkey'):
        return
    for name, (done, find, fixed) in FIXES.items():
        path = MODULE + name
        text = read(path)
        if not text or done in text:
            continue
        if text.count(find) != 1:
            log(f'{name} has changed; its fix was not applied')
            continue
        write(path, text.replace(find, fixed))
        log(f'fixed {name}')


FAILED = b'{"items":[],"pages":0,"count":0}'


def clear_failed_lists():
    """Drop failed requests TMDb Helper cached before the fix above, which left rows empty
    until they expired. Only entries that decode to exactly an empty, page-less list."""
    try:
        import sqlite3
        import zlib
    except ImportError:
        return
    root = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.themoviedb.helper/')
    folders = xbmcvfs.listdir(root)[0]
    for folder in [f for f in folders if f.startswith('database_')]:
        path = f'{root}{folder}/ItemContainer.db'
        if not xbmcvfs.exists(path):
            continue
        try:
            db = sqlite3.connect(path, timeout=5)
            stale = []
            for key, data in db.execute('SELECT id, data FROM simplecache WHERE length(data) < 80'):
                try:
                    raw = data if isinstance(data, bytes) else data.encode('latin-1')
                    if zlib.decompress(raw) == FAILED:
                        stale.append((key,))
                except (zlib.error, UnicodeEncodeError):
                    continue
            if stale:
                db.executemany('DELETE FROM simplecache WHERE id = ?', stale)
                db.commit()
                log(f'cleared {len(stale)} failed lists from the cache')
            db.close()
        except sqlite3.Error as error:
            log(f'could not check the list cache ({error})')


def main():
    state = load_state()
    changed = []
    if state.get('kodi') != VERSION:
        for setting, value in KODI.items():
            set_kodi(setting, value)
        if not xbmcvfs.exists(ADVANCED):
            xbmcvfs.copy(SKIN + 'advancedsettings.xml', ADVANCED)
            changed.append('artwork and streaming (restart Kodi once)')
        state['kodi'] = VERSION
    for addon_id, settings in ADDONS.items():
        if state.get(addon_id) == VERSION or not installed(addon_id):
            continue
        addon = xbmcaddon.Addon(addon_id)
        for key, value in settings.items():
            set_value(addon, key, value)
        state[addon_id] = VERSION
        changed.append(xbmcaddon.Addon(addon_id).getAddonInfo('name'))
        log(f'set up {addon_id}')
    for (addon_id, needs), settings in LINKS.items():
        key = f'{addon_id}+{needs}'
        if state.get(key) == VERSION or not (installed(addon_id) and installed(needs)):
            continue
        addon = xbmcaddon.Addon(addon_id)
        for setting, value in settings.items():
            set_value(addon, setting, value)
        state[key] = VERSION
        log(f'linked {addon_id} to {needs}')
    save_state(state)
    copy_players()
    fix_module()
    clear_failed_lists()
    if changed:
        xbmcgui.Dialog().notification('ATV Minimal', 'Set up: ' + ', '.join(changed),
                                      xbmcgui.NOTIFICATION_INFO, 6000)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:   # never stand between Kodi and Home
        xbmc.log(f'ATV setup failed: {error}', xbmc.LOGWARNING)
