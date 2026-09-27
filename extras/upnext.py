# -*- coding: utf-8 -*-
"""Offer the next episode as the current one finishes.

Kodi lets a skin do nothing by itself while a video plays, and a skin add-on cannot
register a service, so this is a script started by extras/play.py for episodes and left
running alongside playback. It watches the clock, and in the last stretch of the episode
fills in the card at xml/Custom_1150_UpNext.xml and shows it.

    RunScript(special://skin/extras/upnext.py,<tmdb_id>,<season>,<episode>)

The card counts down ten seconds and then plays the next episode - over the credits, as
Netflix and Apple TV do - unless it is dismissed; its Play button starts it at once. Either
way the next episode starts on its own (Auto Play): nobody is there to pick a source.
Choosing to keep watching stops the countdown for good, so it cannot reappear over the
credits of something you decided to stay with.

Where TheIntroDB has timed the episode (extras/segments.py), it also offers Skip Intro and
Skip Recap (xml/Custom_1151_SkipIntro.xml) while those play, and brings the card up as the
credits start - as Apple TV does - instead of a fixed time before the end.
"""
import json
import sys
import threading
import time
from urllib.parse import quote, urlencode

import xbmc
import xbmcgui

import segments
from waiting import Monitor, wait_for_stream  # same folder; on sys.path for RunScript

PLUGIN = 'plugin://plugin.video.themoviedb.helper/?'
WINDOW = 1150
LEAD_IN = 45          # seconds before the end to offer the next episode
CREDITS_LEAD = (15, 600)  # credits starting this far from the end: offer it then instead
SKIP_WINDOW = 1151
COUNTDOWN = 10        # seconds the card counts down before the next episode starts
PRESCRAPE_AT = 300    # seconds before the end: Umbrella searches for the next episode now
                      # (its silent search waits for every provider - 78s on the Mac)
UMBRELLA = 'plugin://plugin.video.umbrella/?'
MIN_RUNTIME = 300     # ignore anything too short to have an "end" worth calling
POLL_MS = 1000
ENDED_WITHIN = 3     # seconds from the end: stopping this close is the episode finishing
START_WAIT = 180     # seconds for the episode to start, not counting time in the source list
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
                     properties=['title', 'season', 'episode', 'art', 'plot', 'premiered', 'uniqueid', 'showtitle'])
    for item in result.get('files') or []:
        if str(item.get('episode')) == str(int(episode) + 1):
            return item
    return None


def prescrape(tmdb_id, item):
    """Umbrella's search for the next episode, now, in the background - so when it is played
    Umbrella finds it in its cache (kept 48h) and skips a search that took 11-22s on the
    Xbox. The values are the ones TMDb Helper's player hands Umbrella (players/umbrella.*.json),
    since they are the cache's key; the action is the skin's patch to Umbrella (setup.py)."""
    ids = item.get('uniqueid') or {}
    show = jsonrpc('Files.GetDirectory', directory=f'{PLUGIN}info=details&tmdb_type=tv&tmdb_id={tmdb_id}&nextpage=false',
                   media='video', properties=['year'])
    year = str(((show.get('files') or [{}])[0]).get('year') or '')
    values = {'title': item.get('title') or '', 'year': year, 'imdb': ids.get('tvshow.imdb', ''),
              'tmdb': str(tmdb_id), 'tvdb': ids.get('tvshow.tvdb', ''), 'season': str(item.get('season')),
              'episode': str(item.get('episode')), 'tvshowtitle': item.get('showtitle') or '',
              'premiered': item.get('premiered') or ''}
    meta = dict(values, code=values['imdb'], label=values['title'], mediatype='episode')
    query = urlencode(dict(values, action='atv_prescrape', meta=json.dumps(meta)), quote_via=quote)
    xbmc.executebuiltin(f'RunPlugin({UMBRELLA}{query})')


def fill_card(tmdb_id, item):
    art = item.get('art') or {}
    for name, value in (
            ('UpNextTitle', item.get('label') or item.get('title') or ''),
            ('UpNextPlot', (item.get('plot') or '')[:240]),
            # Not every episode has a still; the show's own backdrop beats an empty frame.
            ('UpNextThumb', art.get('thumb') or art.get('landscape') or art.get('fanart')
             or xbmc.getInfoLabel('Player.Art(tvshow.fanart)') or xbmc.getInfoLabel('Player.Art(fanart)')
             or art.get('poster') or ''),
            ('UpNextNumber', 'S%s E%s' % (item.get('season'), item.get('episode'))),
            ('UpNextTmdb', str(tmdb_id)),
            ('UpNextSeason', str(item.get('season'))),
            ('UpNextEpisode', str(item.get('episode')))):
        HOME.setProperty(name, value)


def clear_card():
    for name in ('UpNextTitle', 'UpNextPlot', 'UpNextThumb', 'UpNextNumber',
                 'UpNextTmdb', 'UpNextSeason', 'UpNextEpisode', 'UpNextCountdown',
                 'UpNextPlayNow'):
        HOME.clearProperty(name)



def play_next(item, monitor=None):
    """Start the following episode unattended - Auto Play, since nobody is choosing.

    The episode playing is stopped first, and the next asked for once it has gone. Asked for
    while it still played, the hand-over ran alongside TMDb Helper's and Umbrella's busy
    dialogs, and Kodi quits outright on two at once ("two concurrent busydialogs ... The
    application will exit") - which it did on the Xbox, ten seconds into the countdown.
    """
    xbmc.executebuiltin(f'Dialog.Close({WINDOW},true)')
    tmdb_id = HOME.getProperty('UpNextTmdb')
    player, monitor = xbmc.Player(), monitor or Monitor()
    if player.isPlaying():
        player.stop()
        for _ in range(50):                     # up to 5s for playback to wind down
            if not player.isPlaying() or monitor.stopping(0.1):
                break
    if monitor.stopping(0.5):
        return
    xbmc.executebuiltin('RunScript(special://skin/extras/play.py,episode,{},{},{},auto)'.format(
        tmdb_id, item.get('season'), item.get('episode')))


class SkipButton:
    """Skip Intro / Skip Recap, shown while that part plays. Pressed, it seeks past it;
    Back dismisses it; either way it is not offered again for that part."""

    def __init__(self):
        self.current, self.shown_at, self.offered = None, 0.0, set()

    def update(self, player, position, skips):
        if self.current:
            label, start, end = self.current
            if HOME.getProperty('SkipNow') == '1':
                HOME.clearProperty('SkipNow')
                player.seekTime(end)
                self.hide()
            elif not (start - 2 <= position < end - 1):
                self.hide()
            elif time.time() - self.shown_at > 2 and \
                    not xbmc.getCondVisibility(f'Window.IsVisible({SKIP_WINDOW})'):
                self.current = None                         # dismissed with Back
            return
        for part in skips:
            label, start, end = part
            if part not in self.offered and start <= position < end - 3:
                self.offered.add(part)
                self.current, self.shown_at = part, time.time()
                HOME.setProperty('SkipLabel', f'Skip {label}')
                xbmc.executebuiltin(f'ActivateWindow({SKIP_WINDOW})')
                return

    def hide(self):
        if self.current:
            xbmc.executebuiltin(f'Dialog.Close({SKIP_WINDOW},true)')
        self.current = None


def watch(tmdb_id, season, episode):
    monitor, player = Monitor(), xbmc.Player()
    shown, shown_at, prescraped = False, 0.0, False
    remaining_at_last, following = LEAD_IN + 1, None
    found, skip = {}, SkipButton()
    threading.Thread(target=lambda: found.update(segments.fetch(tmdb_id, season, episode)), daemon=True).start()
    if not wait_for_stream(player, START_WAIT, monitor):
        return
    try:
        while not monitor.stopping(POLL_MS / 1000.0):
            try:
                if not player.isPlayingVideo():
                    # Ended with the card up and nothing chosen: that is the countdown
                    # running out, so the next episode starts - as the card promised.
                    # Stopped part-way instead, and the offer lapses with it.
                    if shown and remaining_at_last <= ENDED_WITHIN:
                        play_next(following, monitor)
                    return
                total, position = player.getTotalTime(), player.getTime()
            except RuntimeError:
                return
            if total < MIN_RUNTIME:
                return
            remaining = total - position
            remaining_at_last = remaining
            credits = found.get('credits')
            lead = total - credits if credits and CREDITS_LEAD[0] <= total - credits <= CREDITS_LEAD[1] else LEAD_IN
            if found.get('skips') and not shown:
                skip.update(player, position, found['skips'])
            if shown:
                if HOME.getProperty('UpNextPlayNow') == '1':      # Play on the card
                    HOME.clearProperty('UpNextPlayNow')
                    play_next(following, monitor)
                    return
                # The card is up. Dismissing it, or seeking back into the episode,
                # takes it down and ends the offer for this episode.
                if HOME.getProperty('UpNextDismissed') == '1' or remaining > lead + 30:
                    HOME.clearProperty('UpNextDismissed')
                    xbmc.executebuiltin(f'Dialog.Close({WINDOW},true)')
                    return
                left = COUNTDOWN - (time.time() - shown_at)
                if left <= 0:
                    play_next(following, monitor)
                    return
                HOME.setProperty('UpNextCountdown', str(max(1, int(left + 0.99))))
                continue
            if remaining <= PRESCRAPE_AT + lead - LEAD_IN and not prescraped:
                prescraped = True
                following = following or episode_after(tmdb_id, season, episode)
                if following and xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.umbrella)'):
                    prescrape(tmdb_id, following)
            if remaining > lead:
                continue
            skip.hide()
            following = following or episode_after(tmdb_id, season, episode)
            if not following:
                return
            fill_card(tmdb_id, following)
            HOME.setProperty('UpNextCountdown', str(COUNTDOWN))
            xbmc.executebuiltin(f'ActivateWindow({WINDOW})')
            shown, shown_at = True, time.time()
    finally:
        skip.hide()
        HOME.clearProperty('SkipNow')
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
