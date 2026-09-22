# -*- coding: utf-8 -*-
"""Offer the next episode as the current one finishes.

Kodi lets a skin do nothing by itself while a video plays, and a skin add-on cannot
register a service, so this is a script started by extras/play.py for episodes and left
running alongside playback. It watches the clock, and in the last stretch of the episode
fills in the card at xml/Custom_1150_UpNext.xml and shows it.

    RunScript(special://skin/extras/upnext.py,<tmdb_id>,<season>,<episode>)

The card counts down and then plays the next episode, unless it is dismissed. Choosing
to keep watching stops the countdown for good, so it cannot reappear over the credits of
something you decided to stay with.
"""
import json
import sys

import xbmc
import xbmcgui

PLUGIN = 'plugin://plugin.video.themoviedb.helper/?'
WINDOW = 1150
LEAD_IN = 45          # seconds before the end to offer the next episode
MIN_RUNTIME = 300     # ignore anything too short to have an "end" worth calling
POLL_MS = 1000
HOME = xbmcgui.Window(10000)


def jsonrpc(method, **params):
    request = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
    try:
        return json.loads(xbmc.executeJSONRPC(request)).get('result') or {}
    except ValueError:
        return {}


def episode_after(tmdb_id, season, episode):
    """The episode that follows this one, or None at the end of the run.

    Asks TMDb Helper for the season's episodes rather than assuming episode + 1: a
    season can stop at 6, and rolling into a number that does not exist would start a
    scrape that could never succeed.
    """
    path = (f'{PLUGIN}info=episodes&tmdb_type=tv&tmdb_id={tmdb_id}'
            f'&season={season}&nextpage=false')
    result = jsonrpc('Files.GetDirectory', directory=path, media='video',
                     properties=['title', 'season', 'episode', 'art', 'plot'])
    for item in result.get('files') or []:
        if str(item.get('episode')) == str(int(episode) + 1):
            return item
    return None


def fill_card(tmdb_id, item):
    art = item.get('art') or {}
    for name, value in (
            ('UpNextTitle', item.get('label') or item.get('title') or ''),
            ('UpNextPlot', (item.get('plot') or '')[:240]),
            ('UpNextThumb', art.get('thumb') or art.get('poster') or ''),
            ('UpNextNumber', 'S%s E%s' % (item.get('season'), item.get('episode'))),
            ('UpNextTmdb', str(tmdb_id)),
            ('UpNextSeason', str(item.get('season'))),
            ('UpNextEpisode', str(item.get('episode')))):
        HOME.setProperty(name, value)


def clear_card():
    for name in ('UpNextTitle', 'UpNextPlot', 'UpNextThumb', 'UpNextNumber',
                 'UpNextTmdb', 'UpNextSeason', 'UpNextEpisode', 'UpNextCountdown'):
        HOME.clearProperty(name)


def watch(tmdb_id, season, episode):
    monitor, player = xbmc.Monitor(), xbmc.Player()
    shown = False
    try:
        while not monitor.abortRequested():
            if monitor.waitForAbort(POLL_MS / 1000.0):
                return
            try:
                if not player.isPlayingVideo():
                    return
                total, position = player.getTotalTime(), player.getTime()
            except RuntimeError:
                return
            if total < MIN_RUNTIME:
                return
            remaining = total - position
            if shown:
                # The card is up. Dismissing it, or seeking back into the episode,
                # takes it down and ends the offer for this episode.
                if HOME.getProperty('UpNextDismissed') == '1' or remaining > LEAD_IN + 30:
                    HOME.clearProperty('UpNextDismissed')
                    xbmc.executebuiltin(f'Dialog.Close({WINDOW},true)')
                    return
                HOME.setProperty('UpNextCountdown', str(max(0, int(remaining))))
                continue
            if remaining > LEAD_IN:
                continue
            following = episode_after(tmdb_id, season, episode)
            if not following:
                return
            fill_card(tmdb_id, following)
            xbmc.executebuiltin(f'ActivateWindow({WINDOW})')
            shown = True
    finally:
        if shown:
            xbmc.executebuiltin(f'Dialog.Close({WINDOW},true)')
        clear_card()


def main():
    args = sys.argv[1:]
    if len(args) < 3:
        return
    watch(args[0], args[1], args[2])


if __name__ == '__main__':
    main()
