# -*- coding: utf-8 -*-
"""Navigation sounds on or off (Settings -> Navigation sounds).

On is the skin's own quiet ticks (resource.uisounds.atv, which extras/setup.py installs);
off is none.
Kodi keeps this in a setting of its own that no builtin can change, hence a script; the
skin setting only lets the Settings row say which way it is.

    RunScript(special://skin/extras/sounds.py,on|off)
"""
import json
import sys

import xbmc


def main():
    on = (sys.argv[1:] or ['on'])[0] != 'off'
    request = {'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.SetSettingValue',
               'params': {'setting': 'lookandfeel.soundskin', 'value': 'resource.uisounds.atv' if on else ''}}
    xbmc.executeJSONRPC(json.dumps(request))
    xbmc.executebuiltin('Skin.Reset(atv.nosounds)' if on else 'Skin.SetBool(atv.nosounds)')


if __name__ == '__main__':
    main()
