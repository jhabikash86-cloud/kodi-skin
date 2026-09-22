# -*- coding: utf-8 -*-
"""Playback helper: start the right episode, at the right place.

Kodi's PlayMedia() builds a fresh item from a path string, so anything the
container knew about that item - above all its resume point - is thrown away.
And a show's Play button had no way to know which episode comes next, so it
always started at episode 1.

    RunScript(special://skin/extras/play.py,item,<containerid>)   focused item, resumed
    RunScript(special://skin/extras/play.py,show,<tmdb_id>)       next episode of a show
    RunScript(special://skin/extras/play.py,movie,<tmdb_id>)      a movie, resumed

"Next episode" comes from Trakt through TMDb Helper, in this order:

    1. an episode of this show you paused part-way   -> resume that one
    2. the next unwatched episode of this show       -> play from the start
    3. nothing on Trakt for it                       -> S1E1

Resuming is done by seeking once playback is up rather than by handing Kodi a
start offset, because the stream is resolved by a player add-on several seconds
later and any offset set beforehand is lost. If whatever resolved the stream has
already resumed it (some debrid players do), the seek is skipped.
"""
import json
import re
import sqlite3
import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

PLUGIN = 'plugin://plugin.video.themoviedb.helper/?'
RESUME_FLOOR = 60      # ignore a resume point this small - it is a false start
NEARLY_DONE = 0.92     # past this much of the runtime, treat the episode as finished
START_TIMEOUT = 180    # seconds to wait for the player add-on to resolve a stream
SETTLE = 2             # let the player settle before seeking

# When a debrid service refuses a torrent - usually a rights holder's takedown - Torrentio
# hands back a short explainer clip instead of the film, and it plays like any other
# stream. Left alone it looks as though the title itself is broken.
BLOCKED_MARKER = '/videos/failed_'

# Six films are called "Animal". POV matches on the release name, so the Hindi Animal
# (2023) also turns up the French "Le Regne Animal" (2023) - and that one wins the sort,
# being a 55GB cached 4K remux. A release name reads <title>.<year>.<tags>, so the part
# before the year should be the title, give or take a site or group prefix. This only
# warns: a release it misreads costs a notification, never a film that would have played.
SITEISH = re.compile(r'\d|^www$|^(?:com|net|org|info|world|me|to|cc|io|tv)$')
YEAR = re.compile(r'\b(19|20)\d{2}\b')

# Resolving a stream can take fifteen seconds, during which nothing is playing and the
# remote is idle - exactly what extras/trailer.py waits for. This tells it to hold off.
RESOLVING = 'ATVResolving'

# POV caches a title's scrape for a few hours, so pressing Play again replays whatever
# it settled on last time - including a source that was only picked because the better
# ones happened to fail that once. Dropping the cached rows first makes every Play look
# again and take the best that resolves now. POV does the same thing in its own
# "clear and rescrape" action; this is that delete, from the skin.
POV_CACHE = 'special://profile/addon_data/plugin.video.pov/providerscache.db'

# Release names are all POV has to go on, and a lot of titles share a name: searching for
# the Hindi "Animal" (2023) also turns up the French "Le Regne Animal" (2023), which wins
# on sorting because it happens to be a 55GB cached 4K remux. POV can push sources whose
# name carries a language tag to the front - it keeps the quality order inside that group,
# so the best Hindi release still wins - but only for one language at a time, set here per
# play. Names must match POV's own table (modules/meta_lists.py); languages missing from
# it, Malayalam and Kannada among them, simply leave the ordering alone.
POV_ADDON = 'plugin.video.pov'
POV_LANGUAGES = {
    'en': 'English', 'hi': 'Hindi', 'ta': 'Tamil', 'te': 'Telugu', 'bn': 'Bengali',
    'fr': 'French', 'es': 'Spanish', 'de': 'German', 'it': 'Italian', 'ja': 'Japanese',
    'ko': 'Korean', 'zh': 'Chinese', 'ru': 'Russian', 'pt': 'Portuguese', 'ar': 'Arabic',
    'nl': 'Dutch', 'sv': 'Swedish', 'pl': 'Polish', 'tr': 'Turkish',
}


def jsonrpc(method, **params):
    request = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
    try:
        return json.loads(xbmc.executeJSONRPC(request)).get('result') or {}
    except ValueError:
        return {}


def directory(path):
    """Items of a TMDb Helper list, or [] if that route has nothing for us.

    Several Trakt routes raise rather than return an empty list when the show
    has no progress recorded, so callers must cope with [].
    """
    result = jsonrpc(
        'Files.GetDirectory', directory=path, media='video',
        properties=['season', 'episode', 'resume', 'uniqueid', 'file'])
    return result.get('files') or []


def show_id(item):
    return (item.get('uniqueid') or {}).get('tvshow.tmdb')


def resume_seconds(item):
    """Where to pick this item up, or 0 for the beginning."""
    resume = item.get('resume') or {}
    position, total = resume.get('position') or 0, resume.get('total') or 0
    if position < RESUME_FLOOR or (total and position / total > NEARLY_DONE):
        return 0
    return int(position)


def next_episode(tmdb_id):
    """(season, episode, resume) for the episode of this show to play next."""
    # Paused part-way through: the newest pause wins, which is how the list is sorted.
    for item in directory(f'{PLUGIN}info=trakt_ondeck&tmdb_type=tv&nextpage=false'):
        if show_id(item) == str(tmdb_id) and resume_seconds(item):
            return item.get('season'), item.get('episode'), resume_seconds(item)
    # Finished an episode, so Trakt knows which one is next.
    for item in directory(f'{PLUGIN}info=trakt_nextepisodes&tmdb_type=tv&nextpage=false'):
        if show_id(item) == str(tmdb_id):
            return item.get('season'), item.get('episode'), resume_seconds(item)
    return 1, 1, 0


def movie_resume(tmdb_id):
    for item in directory(f'{PLUGIN}info=trakt_ondeck&tmdb_type=movie&nextpage=false'):
        if (item.get('uniqueid') or {}).get('tmdb') == str(tmdb_id):
            return resume_seconds(item)
    return 0


def normalise(text):
    return re.sub(r'[^a-z0-9]+', '.', (text or '').lower()).strip('.')


def release_name(path):
    """The release name out of whatever the debrid service handed back."""
    path = path or ''
    match = re.search(r'torrent_name=([^&]+)', path)
    if match:
        from urllib.parse import unquote_plus
        return unquote_plus(match.group(1))
    return path.rsplit('/', 1)[-1].split('?')[0]


def expected_title(kind, tmdb_id):
    items = directory(f'{PLUGIN}info=details&tmdb_type={kind}&tmdb_id={tmdb_id}&nextpage=false')
    if not items:
        return ''
    return items[0].get('label') or ''


def looks_like_another_film(path, title):
    """True when the release name reads like a different film.

    Two signs, either of which is enough: the words before the year are not the title
    (so "the.animal.kingdom.2024" is not "Animal"), or more than one real word sits in
    front of the title (so "le.regne.animal" is not "animal", while a lone group tag or
    a site prefix like "www.1tamilmv.world" is fine).
    """
    name = normalise(release_name(path))
    wanted = normalise(title)
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


def blocked_stream():
    """True when what is playing is a "this source was taken down" clip, not the title."""
    return BLOCKED_MARKER in (xbmc.getInfoLabel('Player.Filenameandpath') or '').lower()


def prefer_language(code):
    """Ask POV to sort releases in this language to the top for the coming play."""
    name = POV_LANGUAGES.get((code or '').lower())
    try:
        pov = xbmcaddon.Addon(POV_ADDON)
        pov.setSetting('results.language_filter', 'true' if name else 'false')
        if name:
            pov.setSetting('results.language', name)
    except Exception:
        pass  # POV not installed, or settings locked - ordering just stays as it was


def rescrape(kind, tmdb_id):
    """Forget POV's cached sources for one title, so the next play scrapes afresh."""
    try:
        database = xbmcvfs.translatePath(POV_CACHE)
        with sqlite3.connect(database, timeout=2) as connection:
            connection.execute(
                'DELETE FROM results_data WHERE db_type = ? AND tmdb_id = ?', (kind, str(tmdb_id)))
    except Exception:
        pass  # a locked or missing cache just means this play reuses it


def play(path, resume=0, on_blocked=None, title=''):
    """Start `path`, then put it right: skip a takedown clip, and resume where asked.

    `on_blocked` is a builtin run when the stream turns out to be a takedown clip - the
    source picker, so the next source can be chosen instead of being left with a
    30-second notice playing as though it were the film.
    """
    home = xbmcgui.Window(10000)
    home.setProperty(RESOLVING, '1')
    try:
        xbmc.executebuiltin(f'PlayMedia({path})')
        player = xbmc.Player()
        for _ in range(START_TIMEOUT * 4):
            if player.isPlayingVideo():
                break
            xbmc.sleep(250)
        else:
            return  # the user backed out, or nothing could be resolved
    finally:
        home.clearProperty(RESOLVING)
    xbmc.sleep(SETTLE * 1000)
    try:
        if not player.isPlayingVideo():
            # It opened and stopped again within a couple of seconds. That is a source
            # the debrid service never actually had: the stream hits EOF at once. Left
            # alone it looks as though nothing happened at all.
            xbmcgui.Dialog().notification(
                'Source would not play', 'Nothing was cached for it - pick another',
                xbmcgui.NOTIFICATION_INFO, 4000)
            if on_blocked:
                xbmc.sleep(500)
                xbmc.executebuiltin(on_blocked)
            return
        if title and looks_like_another_film(xbmc.getInfoLabel('Player.Filenameandpath'), title):
            # Only a warning. Getting this wrong must never cost a film that would play.
            xbmcgui.Dialog().notification(
                'This may not be ' + title, 'Use Sources to pick another release',
                xbmcgui.NOTIFICATION_INFO, 6000)
        if blocked_stream():
            player.stop()
            xbmcgui.Dialog().notification(
                'Source blocked', 'That release was taken down - pick another',
                xbmcgui.NOTIFICATION_INFO, 4000)
            if on_blocked:
                xbmc.sleep(500)
                xbmc.executebuiltin(on_blocked)
            return
        if not resume:
            return
        if player.getTime() > resume - 30:
            return  # the player add-on resumed it for us
        player.seekTime(resume)
    except RuntimeError:
        pass  # playback ended while we were waiting


def play_item(container):
    """The focused item of a container - it already knows its own path and progress.

    Kodi folds a plugin's ResumeTime/TotalTime properties into the item's info tag and
    does not hand them back, so the position is reconstructed from PercentPlayed. That
    is a whole percent, so it can land a few seconds early - which is the right side to
    err on.
    """
    prefix = f'Container({container}).ListItem'
    path = xbmc.getInfoLabel(f'{prefix}.FileNameAndPath')
    if not path:
        return
    prefer_language(xbmc.getInfoLabel(f'{prefix}.Property(original_language)'))
    try:
        percent = int(xbmc.getInfoLabel(f'{prefix}.PercentPlayed') or 0)
        duration = int(xbmc.getInfoLabel(f'{prefix}.Duration(secs)') or 0)
    except ValueError:
        percent = duration = 0
    resume = int(duration * percent / 100)
    if resume < RESUME_FLOOR or percent > NEARLY_DONE * 100:
        resume = 0
    play(path, resume)


def play_show(tmdb_id, lang=None):
    if not tmdb_id:
        return
    season, episode, resume = next_episode(tmdb_id)
    prefer_language(lang)
    rescrape('episode', tmdb_id)
    show_title = expected_title('tv', tmdb_id)
    play(f'{PLUGIN}info=play&tmdb_type=tv&tmdb_id={tmdb_id}&season={season}&episode={episode}', resume,
         title=show_title,
         on_blocked=(f'RunScript(plugin.video.themoviedb.helper,play=tv,tmdb_id={tmdb_id},'
                     f'season={season},episode={episode},ignore_default=True)'))


def play_movie(tmdb_id, lang=None):
    if not tmdb_id:
        return
    prefer_language(lang)
    rescrape('movie', tmdb_id)
    film_title = expected_title('movie', tmdb_id)
    play(f'{PLUGIN}info=play&tmdb_type=movie&tmdb_id={tmdb_id}', movie_resume(tmdb_id),
         title=film_title,
         on_blocked=(f'RunScript(plugin.video.themoviedb.helper,play=movie,'
                     f'tmdb_id={tmdb_id},ignore_default=True)'))


def main():
    args = sys.argv[1:]
    action = args[0] if args else ''
    target = args[1] if len(args) > 1 else ''
    lang = args[2] if len(args) > 2 else None
    if action == 'item':
        play_item(target)
    elif action == 'show':
        play_show(target, lang)
    elif action == 'movie':
        play_movie(target, lang)


if __name__ == '__main__':
    main()
