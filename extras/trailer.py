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
import xbmc
import xbmcgui

POLL_MS = 250
DWELL = 2            # seconds of stillness before a preview starts
PROPERTY = 'ATVPreview'
RUNNING = 'ATVPreviewWatcher'
RESOLVING = 'ATVResolving'   # extras/play.py sets this while it waits for a stream

# The hero's own buttons. A skin <expression> cannot be used here: getCondVisibility
# does not expand $EXP[], it just returns False, which is why this has to name the
# controls itself.
HERO_FOCUSED = 'Control.HasFocus(8001) | Control.HasFocus(8002) | Control.HasFocus(8003)'
HOME = xbmcgui.Window(10000)


def info(label):
    return xbmc.getInfoLabel(label)


def visible(condition):
    return xbmc.getCondVisibility(condition)


class Preview:
    """Starts and stops the hero preview, and remembers whether it owns what is playing."""

    def __init__(self):
        self.player = xbmc.Player()
        self.showing = None   # the trailer url we started, or None

    def start(self, url):
        item = xbmcgui.ListItem(path=url)
        item.setProperty('IsPlayable', 'true')
        HOME.setProperty(PROPERTY, '1')
        self.showing = url
        try:
            self.player.play(url, item, windowed=True)
        except Exception:
            self.stop()

    def forget(self):
        """Give up the claim without touching the player - something else owns it now."""
        self.showing = None
        HOME.clearProperty(PROPERTY)

    def stop(self):
        if self.showing is None:
            return
        self.showing = None
        HOME.clearProperty(PROPERTY)
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
    monitor = xbmc.Monitor()
    preview = Preview()
    try:
        while not monitor.abortRequested():
            if monitor.waitForAbort(POLL_MS / 1000.0):
                break
            if not visible('Window.IsActive(home)'):
                preview.stop()
                break
            # The hero is only on screen while its own buttons have focus; moving into
            # the rows scrolls it away, so anything playing should go with it.
            on_hero = visible(HERO_FOCUSED)
            trailer = info('Container(40).ListItem.Trailer')
            if preview.showing and HOME.getProperty(RESOLVING) == '1':
                preview.stop()   # a real play is being resolved; get out of its way
                continue
            if preview.showing and visible('Player.HasMedia') \
                    and info('Player.Filenameandpath') != preview.showing:
                preview.forget()  # a film is playing now - leave it alone
                continue
            if preview.showing:
                # Any button press ends the preview, the way it does on an Apple TV -
                # and it has to, or pressing Play would start the film underneath a
                # trailer that is still running.
                touched = not visible('System.IdleTime(1)')
                if touched or (trailer and trailer != preview.showing):
                    preview.stop()
                continue
            if preview.showing or preview.someone_else_is_playing():
                continue
            if on_hero and trailer and visible(f'System.IdleTime({DWELL})'):
                preview.start(trailer)
    finally:
        preview.stop()
        HOME.clearProperty(RUNNING)


if __name__ == '__main__':
    watch()
