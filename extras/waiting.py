# -*- coding: utf-8 -*-
"""Waiting on Kodi, for the skin's scripts: for a stream to start, and for Kodi to quit.

    from waiting import Monitor, wait_for_stream   # same folder; Kodi puts a RunScript's
                                                    # directory on sys.path
"""
import time

import xbmc

# Umbrella's source list (13001) and its progress window (13000), and Kodi's busy dialogs.
# While any is up, a play is still on its way - however long you spend choosing.
PICKING = 'Window.IsActive(13000) | Window.IsActive(13001)'
BUSY = 'Window.IsActive(10138) | Window.IsActive(10160)'
BACKED_OUT = 10   # seconds with the list gone and nothing playing: you pressed Back


class Monitor(xbmc.Monitor):
    """Knows Kodi is quitting as soon as Kodi says so.

    Kodi only asks a skin's scripts to stop after it has unloaded the skin, and by then the
    GUI calls a waiting loop makes are stuck behind a Kodi that is busy shutting down: the
    script never sees the request, Kodi kills it after 5s, and on a bad exit never finishes
    quitting. System.OnQuit arrives at the start of shutdown, while there is still time to
    leave cleanly.
    """

    quitting = False

    def onNotification(self, sender, method, data):
        if method in ('System.OnQuit', 'System.OnRestart'):
            self.quitting = True

    def stopping(self, seconds=0):
        """Wait up to `seconds`, then True if Kodi is going away."""
        if self.quitting or (self.waitForAbort(seconds) if seconds else self.abortRequested()):
            return True
        return self.quitting


def real_stream(player):
    """True once the stream itself is playing.

    With a resolvable player such as Umbrella, TMDb Helper plays a tiny placeholder first -
    dummy.mp4 - and swaps the real stream in once it is resolved. Taking the placeholder
    for playback meant a resume point was never applied, and the Up Next watcher quit
    before the episode began.
    """
    try:
        return player.isPlayingVideo() and not player.getPlayingFile().endswith('dummy.mp4')
    except RuntimeError:
        return False


def wait_for_stream(player, timeout, monitor=None):
    """Wait for the real stream; True if it started.

    The clock stops while the source list is open - that is you choosing. Once the list has
    been up, it gives up BACKED_OUT seconds after the list, the progress window and Kodi's
    busy dialog have all gone with nothing playing: that is Back. Waiting on for the full
    timeout kept the hero's trailers switched off for minutes after a cancelled Play.
    """
    monitor = monitor or Monitor()
    waited, picked, idle_since = 0.0, False, None
    while waited < timeout:
        if real_stream(player):
            return True
        if monitor.stopping(0.25):
            return False
        picking = xbmc.getCondVisibility(PICKING)
        if picking:
            picked, idle_since = True, None
            continue
        waited += 0.25
        if picked and not xbmc.getCondVisibility(BUSY) and not player.isPlaying():
            idle_since = idle_since or time.time()
            if time.time() - idle_since > BACKED_OUT:
                return False
        else:
            idle_since = None
    return False
