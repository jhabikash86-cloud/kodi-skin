# -*- coding: utf-8 -*-
"""Remove the focused title from Continue Watching.

Continue Watching is Trakt's playback progress, so removing a tile means deleting that saved
position on Trakt - TMDb Helper's own "progress" sync does it with your Trakt login. Opened
from the skin's first context-menu entry (xml/DialogContextMenu.xml), which shows on
anything on Home with viewing progress. The film or episode itself is not marked watched.

TMDb Helper reports the result in an OK box. A success needs no answer, so it is closed and
the tile simply goes; a failure is left up, since it says why.

    RunScript(special://skin/extras/forget.py)
"""
import time

import xbmc
import xbmcaddon
import xbmcgui

HOME = xbmcgui.Window(10000)
HELPER = 'plugin.video.themoviedb.helper'
RELOAD = 'ATVContinueReload'   # Continue Watching's rows carry it in their path
ROWS = (50, 51)                # Continue Watching, Continue Watching Films
REPLY_WAIT = 15                # seconds for TMDb Helper to answer: it asks Trakt twice
OK_DIALOG = 'Window.IsActive(okdialog)'


def info(label):
    return xbmc.getInfoLabel(label)


def focused_item():
    """(kind, tmdb id, season, episode) of the tile the menu was opened on."""
    if info('ListItem.DBType') == 'episode':
        return ('tv', info('ListItem.Property(tvshow.tmdb_id)'),
                info('ListItem.Season'), info('ListItem.Episode'))
    return 'movie', info('ListItem.UniqueID(tmdb)'), '', ''


def remaining():
    return sum(int(info(f'Container({row}).NumItems') or 0) for row in ROWS)


def success_text():
    """The words TMDb Helper's success message has and its failure message lacks:
    "{} was successful for {}!" - in whatever language Kodi is in."""
    try:
        parts = xbmcaddon.Addon(HELPER).getLocalizedString(32297).split('{}')
        return parts[1].strip() if len(parts) > 2 else ''
    except RuntimeError:
        return ''


def await_reply(monitor):
    """Wait for TMDb Helper's OK box; close it if it reports success. False on a failure."""
    deadline = time.time() + REPLY_WAIT
    while time.time() < deadline:
        if xbmc.getCondVisibility(OK_DIALOG):
            words = success_text()
            if words and words not in info('Control.GetLabel(9)'):
                return False
            xbmc.executebuiltin('Dialog.Close(okdialog)')
            return True
        if monitor.waitForAbort(0.2):
            return False
    return True   # no box: nothing was saved on Trakt for it, which is what we wanted


def main():
    kind, tmdb_id, season, episode = focused_item()
    if not tmdb_id:
        return
    args = f'tmdb_type={kind},tmdb_id={tmdb_id}'
    if kind == 'tv':
        args += f',season={season},episode={episode}'
    before = remaining()
    xbmc.executebuiltin(f'RunScript({HELPER},sync_trakt,{args},sync_type=progress)')
    monitor = xbmc.Monitor()
    if not await_reply(monitor):
        return
    # A changed path makes Kodi fetch the rows again, and TMDb Helper re-reads Trakt after a
    # sync. Twice, in case the first is too early.
    for wait in (1, 5):
        if monitor.waitForAbort(wait):
            return
        HOME.setProperty(RELOAD, str(time.time()))
        if monitor.waitForAbort(3) or remaining() < before:
            return
    xbmcgui.Dialog().notification('Continue Watching', "Trakt still has it - try again in a minute",
                                  xbmcgui.NOTIFICATION_WARNING, 4000)


if __name__ == '__main__':
    main()
