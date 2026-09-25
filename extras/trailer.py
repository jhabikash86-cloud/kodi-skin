# -*- coding: utf-8 -*-
"""Play the hero's trailer once you have been still on it for a moment.

Kodi gives a skin no way to time how long an item has been focused, and no event at
all when the focused *item* of a list changes. So this runs as a loop started by the
window's <onload> and stopped by its <onunload>, watching two things: how long the
remote has been idle, and which item the hero is showing.

Playback is windowed - xbmc.Player().play(..., windowed=True) - so Kodi does not
switch to full screen. Home draws it inside the hero's own frame through a
<control type="videowindow">, gated on the ATVPreview property this sets.

    RunScript(special://skin/extras/trailer.py,watch)
"""
import re
import time

import xbmc
import xbmcgui

from waiting import Monitor  # same folder; Kodi puts a RunScript's directory on sys.path

POLL_MS = 250
# Seconds of stillness before a preview starts. While the YouTube add-on looks a trailer
# up - 2-40s here - Kodi shows a modal busy dialog that ignores every key but Back, so a
# lookup started while you are still browsing eats your next press. Four seconds keeps
# lookups to when you have stopped to look at the hero.
DWELL = 4
BUSY = 'Window.IsActive(10138) | Window.IsActive(10160)'   # Kodi's busy dialogs
OFF = 'Skin.HasSetting(atv.notrailers)'                     # Settings -> Banner trailers
# How long a trailer gets to start. YouTube lookups measured 8-31s here, and slower the
# more trailers were asked for. At 10s the watcher gave up on most of them, the hero moved
# on, and the trailer then arrived late for a title no longer shown - playing as sound
# with its picture hidden, which is what "trailers only play the sound" was.
GRACE = 40
PROPERTY = 'ATVPreview'
RUNNING = 'ATVPreviewWatcher'
RESOLVING = 'ATVResolving'   # extras/play.py sets this while it waits for a stream

# Studios post square and vertical cuts for social media under the same "Trailer" label,
# often with captions burned into the picture. In the hero they sit boxed in the middle
# of the frame with their captions running into the plot. Nothing in TMDb's video list
# tells them apart, so the picture decides: anything narrower than this is stopped and
# the hero keeps its backdrop.
MIN_ASPECT = 1.6
SHAPE = 'ATVPreviewShape'   # set once the picture has passed; Home shows the video only then
REJECTED = 'ATVPreviewRejected'  # kept on Home, so a restarted watcher remembers too
SETTLED = 1.0        # seconds in before the aspect can be trusted - it holds the last video's until then

# The hero's own buttons, and the tab bar above it: coming back to Home through the tab
# bar leaves focus up there, with the whole hero in view, and a hero that kept sliding by
# without ever playing a trailer read as the trailers being broken. A skin <expression>
# cannot be used here: getCondVisibility does not expand $EXP[], it just returns False,
# which is why this has to name the controls itself.
HERO_FOCUSED = ('Control.HasFocus(8001) | Control.HasFocus(8002) | Control.HasFocus(8003)'
                ' | ControlGroup(9000).HasFocus(0)')
HOME = xbmcgui.Window(10000)


def video_id(url):
    """The YouTube id in a trailer link, or ''."""
    match = re.search(r'video_id=([\w-]{6,})', url or '')
    return match.group(1) if match else ''



def info(label):
    return xbmc.getInfoLabel(label)


def visible(condition):
    return xbmc.getCondVisibility(condition)


class Preview:
    """Starts and stops the hero preview, and remembers whether it owns what is playing."""

    def __init__(self):
        self.player = xbmc.Player()
        self.showing = None   # the trailer url we started, or None
        self.started = 0.0
        self.checked = False  # whether this preview's shape has been looked at yet
        self.started_playing = False
        self.abandoned = {}   # trailers stopped before they started: url -> when

    def start(self, url):
        item = xbmcgui.ListItem(path=url)
        item.setProperty('IsPlayable', 'true')
        HOME.setProperty(PROPERTY, '1')
        self.showing = url
        self.started = time.time()
        self.checked = False
        self.started_playing = False
        HOME.clearProperty(SHAPE)
        try:
            self.player.play(url, item, windowed=True)
        except Exception:
            self.stop()

    def forget(self):
        """Give up the claim without touching the player - something else owns it now."""
        self.showing = None
        HOME.clearProperty(PROPERTY)
        HOME.clearProperty(SHAPE)

    def ended(self):
        """True once the trailer has played and finished."""
        try:
            playing = self.player.isPlayingVideo()
        except RuntimeError:
            playing = False
        if playing:
            self.started_playing = True
            return False
        return self.started_playing

    def arrived_late(self):
        """True, once, when what is playing is a trailer this watcher already let go of.

        Asks the player for the file itself - Kodi's Player.Filenameandpath label still holds
        the previous file for a moment after a new one starts, and reading it stopped an
        episode that happened to start just after a trailer was abandoned. The player may
        name the stream by its resolved address rather than the add-on link, so the match
        is on the YouTube video id, which both carry.
        """
        now = time.time()
        self.abandoned = {u: t for u, t in self.abandoned.items() if now - t < GRACE + 20}
        if not self.abandoned:
            return False
        try:
            playing = self.player.getPlayingFile()
        except RuntimeError:
            return False
        for url in list(self.abandoned):
            video = video_id(url)
            if video and video in playing:
                del self.abandoned[url]
                return True
        return False

    def gave_up(self):
        """True when the trailer has not started in GRACE seconds. It is skipped for the rest
        of the session: a lookup that slow is YouTube throttling, and waiting on it again
        would only hold the hero still for nothing."""
        if self.started_playing or time.time() - self.started < GRACE:
            return False
        HOME.setProperty(REJECTED, HOME.getProperty(REJECTED) + '\n' + self.showing)
        return True

    def wrong_shape(self):
        """True, once, if what is playing is a square or vertical cut."""
        if self.checked:
            return False
        try:
            if not self.player.isPlayingVideo() or self.player.getTime() < SETTLED:
                return False
        except RuntimeError:
            return False
        self.checked = True
        try:
            aspect = float(info('VideoPlayer.VideoAspect') or 0)
        except ValueError:
            return False
        if 0 < aspect < MIN_ASPECT:
            HOME.setProperty(REJECTED, HOME.getProperty(REJECTED) + '\n' + self.showing)
            return True
        HOME.setProperty(SHAPE, '1')
        return False

    def stop(self):
        if self.showing is None:
            return
        if not self.started_playing:
            # Its lookup is still running and it may yet start; remember it, so that - and
            # only that - is stopped if it does.
            self.abandoned[self.showing] = time.time()
        self.showing = None
        HOME.clearProperty(PROPERTY)
        HOME.clearProperty(SHAPE)
        try:
            if self.player.isPlaying():
                self.player.stop()
        except Exception:
            pass

    def someone_else_is_playing(self):
        """True when a real film is on, or on its way - never start over either."""
        if HOME.getProperty(RESOLVING) == '1':
            return True
        return self.showing is None and visible('Player.HasMedia')


def watch():
    if HOME.getProperty(RUNNING) == '1':
        return  # one watcher is enough; the window can trigger this more than once
    HOME.setProperty(RUNNING, '1')
    monitor = Monitor()
    preview = Preview()
    try:
        while not monitor.stopping(POLL_MS / 1000.0):
            if not visible('Window.IsActive(home)'):
                break
            if HOME.getProperty(REJECTED).count('\n') > 200:
                HOME.setProperty(REJECTED, '')      # a long session; let them be tried again

            # A real play is on its way. Resolving takes long enough that the remote goes
            # idle with nothing playing, which is exactly the cue below, so this comes first.
            if HOME.getProperty(RESOLVING) == '1':
                preview.stop()
                continue

            trailer = info('Container(40).ListItem.Trailer')
            if preview.showing:
                if preview.ended():
                    preview.forget()        # the trailer simply ended
                elif preview.gave_up():
                    preview.stop()          # YouTube never delivered it
                elif not preview.started_playing and not visible('System.IdleTime(1)') and visible(BUSY):
                    # A key pressed while the lookup still holds the busy dialog: that press
                    # went to the dialog. Cancel the lookup - Back is the one key the dialog
                    # takes - so the next press reaches Home at once, not up to 40s later.
                    xbmc.executebuiltin('Action(Back)')
                    preview.stop()
                elif preview.wrong_shape():
                    preview.stop()          # a social-media cut; the backdrop is better
                elif not visible('System.IdleTime(1)'):
                    preview.stop()          # any button press ends a preview
                elif trailer and trailer != preview.showing:
                    preview.stop()          # the hero moved on to another title
                continue

            # A trailer arriving after the preview was stopped or given up on - its lookup was
            # still running. Stopped once; anything else playing is left alone.
            if visible('Player.HasMedia') and preview.arrived_late():
                try:
                    preview.player.stop()
                except RuntimeError:
                    pass
                continue

            # Never start over something else - a film.
            if visible('Player.HasMedia'):
                continue
            if trailer and trailer in HOME.getProperty(REJECTED).split('\n'):
                continue
            if visible(OFF):
                continue
            if visible(HERO_FOCUSED) and trailer and visible(f'System.IdleTime({DWELL})'):
                preview.start(trailer)
    finally:
        if monitor.quitting or monitor.abortRequested():
            # Kodi is quitting and stops the player itself. Stopping it from here can block
            # while a YouTube stream is still opening - Kodi then killed this script after
            # 5s and never finished exiting - so only let go of the hero.
            HOME.clearProperty(PROPERTY)
            HOME.clearProperty(SHAPE)
        else:
            preview.stop()
        HOME.clearProperty(RUNNING)


if __name__ == '__main__':
    watch()
