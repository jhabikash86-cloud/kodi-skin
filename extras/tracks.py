# -*- coding: utf-8 -*-
"""Audio & Subtitles, as Apple TV's player: one panel with the playing file's audio tracks,
its subtitles and a few options, the ones in use ticked (xml/ATVTracks.xml).

Kodi splits these over two settings dialogs and names a track only by its codec; here each
row says what it is - "English", "Dolby TrueHD  ·  7.1  ·  Original" - and picking one
switches to it at once, the panel staying open so you can hear or read the change.

    RunScript(special://skin/extras/tracks.py)      # the subtitles button, VideoOSD.xml
"""
import json
import re

import xbmc
import xbmcgui
import xbmcvfs

AUDIO, SUBTITLES, OPTIONS = 100, 200, 300
BACK = (9, 10, 92)      # parent dir, previous menu, back

CODECS = {
    'truehd': 'Dolby TrueHD', 'eac3': 'Dolby Digital Plus', 'ac3': 'Dolby Digital',
    'dtshd_ma': 'DTS-HD Master Audio', 'dtshd_hra': 'DTS-HD High Resolution', 'dtshd': 'DTS-HD',
    'dca': 'DTS', 'dts': 'DTS', 'aac': 'AAC', 'flac': 'FLAC', 'opus': 'Opus', 'mp3': 'MP3',
    'vorbis': 'Vorbis', 'pcm': 'PCM', 'lpcm': 'PCM',
}
CHANNELS = {1: 'Mono', 2: 'Stereo', 3: '2.1', 6: '5.1', 7: '6.1', 8: '7.1'}

# Options: label, what it is, and the builtins that open it (after the panel closes)
MORE = [
    ('Find Subtitles', 'Search the subtitle services', 'ActivateWindow(SubtitleSearch)'),
    ('Subtitle Timing & Style', 'Delay, size and position', 'ActivateWindow(osdsubtitlesettings)'),
    ('Audio Sync & Level', 'Delay and volume boost', 'ActivateWindow(osdaudiosettings)'),
]


def rpc(method, params=None):
    request = {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(request))).get('result')
    except (ValueError, TypeError):
        return None


def video_player():
    for player in rpc('Player.GetActivePlayers') or []:
        if player.get('type') == 'video':
            return player.get('playerid')
    return None


def language(code):
    if not code or code in ('und', 'unk', 'zxx', 'mis'):
        return ''
    return xbmc.convertLanguage(code, xbmc.ENGLISH_NAME) or code


NOISE = re.compile(r'(?<!\w)(dolby|truehd|true-hd|atmos|dts(-?hd)?|ma|hra|x|e-?ac-?3|ac-?3|dd\+?|ddp|digital|plus|'
                   r'aac(-lc)?|flac|opus|pcm|lpcm|mp3|stereo|mono|surround|audio|\d\.\d(ch)?|\d+ ?ch|\d+ ?kbps|\d+)(?!\w)', re.I)


def own_words(title):
    """What a track's name says beyond its codec and channels ("Commentary with director")."""
    return re.sub(r'[\s\-/|,()\[\]+.]+', ' ', NOISE.sub(' ', title)).strip()


def audio_row(stream, others):
    name = language(stream.get('language'))
    title = (stream.get('name') or '').strip()
    raw = (stream.get('codec') or '').lower()
    codec = CODECS.get(raw, raw.upper())
    if 'atmos' in title.lower() and raw in ('truehd', 'eac3'):
        codec += ' Atmos'
    details = [codec, CHANNELS.get(stream.get('channels'), f"{stream.get('channels')}ch" if stream.get('channels') else '')]
    if stream.get('isoriginal'):
        details.append('Original')
    if stream.get('isimpaired'):
        details.append('Audio Description')
    extra = own_words(title)
    label = name or extra or f"Track {stream.get('index', 0) + 1}"
    # Two tracks in the same language: the track's own name tells them apart
    if name and extra and extra.lower() != name.lower() and \
            sum(1 for s in others if language(s.get('language')) == name) > 1:
        label = f'{name} ({extra})'
    return label, '  ·  '.join(d for d in details if d)


def subtitle_row(stream):
    name = language(stream.get('language'))
    title = (stream.get('name') or '').strip()
    tags = []
    if stream.get('isimpaired') or 'sdh' in title.lower():
        tags.append('SDH')
    if stream.get('isforced') or 'forced' in title.lower():
        tags.append('Forced')
    label = name or title or f"Subtitle {stream.get('index', 0) + 1}"
    if tags:
        label += f" ({', '.join(tags)})"
    rest = [w for w in re.findall(r'\w+', title) if w.lower() not in label.lower()]
    detail = title if rest else ''
    return label, detail


class Tracks(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        self.player = kwargs.pop('player')
        self.after = None
        super().__init__(*args, **kwargs)

    def onInit(self):
        state = rpc('Player.GetProperties', {'playerid': self.player, 'properties': [
            'audiostreams', 'currentaudiostream', 'subtitles', 'currentsubtitle', 'subtitleenabled']}) or {}
        audio = state.get('audiostreams') or []
        current_audio = (state.get('currentaudiostream') or {}).get('index')
        self.fill(AUDIO, [(s['index'],) + audio_row(s, audio) for s in audio], current_audio)

        subtitles = state.get('subtitles') or []
        on = state.get('subtitleenabled') and subtitles
        current_sub = (state.get('currentsubtitle') or {}).get('index') if on else 'off'
        rows = [('off', 'Off', '')] + [(s['index'],) + subtitle_row(s) for s in subtitles]
        self.fill(SUBTITLES, rows, current_sub)

        self.fill(OPTIONS, [(cmd, label, what) for label, what, cmd in MORE], None)
        # the panel is as tall as its longest column (ATVTracks.xml)
        xbmcgui.Window(10000).setProperty('ATVTracksRows', str(min(6, max(len(audio), len(rows), len(MORE)))))
        self.setFocusId(AUDIO if audio else SUBTITLES)

    def fill(self, control_id, rows, current):
        items = []
        for value, label, detail in rows:
            item = xbmcgui.ListItem(label, detail, offscreen=True)
            item.setProperty('value', str(value))
            if value == current:
                item.setProperty('selected', 'true')
            items.append(item)
        control = self.getControl(control_id)
        control.reset()
        control.addItems(items)
        for i, (value, _, _) in enumerate(rows):
            if value == current:
                control.selectItem(i)

    def tick(self, control):
        chosen = control.getSelectedPosition()
        for i in range(control.size()):
            control.getListItem(i).setProperty('selected', 'true' if i == chosen else '')

    def onClick(self, control_id):
        control = self.getControl(control_id)
        item = control.getSelectedItem()
        if not item:
            return
        value = item.getProperty('value')
        if control_id == AUDIO:
            rpc('Player.SetAudioStream', {'playerid': self.player, 'stream': int(value)})
            self.tick(control)
        elif control_id == SUBTITLES:
            if value == 'off':
                rpc('Player.SetSubtitle', {'playerid': self.player, 'subtitle': 'off'})
            else:
                rpc('Player.SetSubtitle', {'playerid': self.player, 'subtitle': int(value), 'enable': True})
            self.tick(control)
        elif control_id == OPTIONS:
            self.after = value
            self.close()

    def onAction(self, action):
        if action.getId() in BACK:
            self.close()


def main():
    player = video_player()
    if player is None:
        return
    xbmc.executebuiltin('Dialog.Close(VideoOSD,true)')
    dialog = Tracks('ATVTracks.xml', xbmcvfs.translatePath('special://skin/'), 'Default', '1080i', player=player)
    dialog.doModal()
    after = dialog.after
    del dialog
    if after:
        xbmc.executebuiltin(after)


if __name__ == '__main__':
    main()
