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
import sys

import xbmc
import xbmcgui

PLUGIN = 'plugin://plugin.video.themoviedb.helper/?'
RESUME_FLOOR = 60      # ignore a resume point this small - it is a false start
NEARLY_DONE = 0.92     # past this much of the runtime, treat the episode as finished
START_TIMEOUT = 180    # seconds to wait for the player add-on to resolve a stream
SETTLE = 2             # let the player settle before seeking


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


def play(path, resume=0):
    xbmc.executebuiltin(f'PlayMedia({path})')
    if not resume:
        return
    player = xbmc.Player()
    for _ in range(START_TIMEOUT * 4):
        if player.isPlayingVideo():
            break
        xbmc.sleep(250)
    else:
        return  # the user backed out, or nothing could be resolved
    xbmc.sleep(SETTLE * 1000)
    try:
        if not player.isPlayingVideo():
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
    try:
        percent = int(xbmc.getInfoLabel(f'{prefix}.PercentPlayed') or 0)
        duration = int(xbmc.getInfoLabel(f'{prefix}.Duration(secs)') or 0)
    except ValueError:
        percent = duration = 0
    resume = int(duration * percent / 100)
    if resume < RESUME_FLOOR or percent > NEARLY_DONE * 100:
        resume = 0
    play(path, resume)


def play_show(tmdb_id):
    if not tmdb_id:
        return
    xbmcgui.Window(10000).setProperty('ATVResolving', '1')
    try:
        season, episode, resume = next_episode(tmdb_id)
    finally:
        xbmcgui.Window(10000).clearProperty('ATVResolving')
    play(f'{PLUGIN}info=play&tmdb_type=tv&tmdb_id={tmdb_id}&season={season}&episode={episode}', resume)


def play_movie(tmdb_id):
    if not tmdb_id:
        return
    play(f'{PLUGIN}info=play&tmdb_type=movie&tmdb_id={tmdb_id}', movie_resume(tmdb_id))


def main():
    args = sys.argv[1:]
    action = args[0] if args else ''
    target = args[1] if len(args) > 1 else ''
    if action == 'item':
        play_item(target)
    elif action == 'show':
        play_show(target)
    elif action == 'movie':
        play_movie(target)


if __name__ == '__main__':
    main()
