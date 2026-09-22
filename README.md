# ATV Minimal

A Kodi 21 (Omega) skin in the shape of Apple TV, with Netflix-style search.
Forked from Estuary; add-on id `skin.appletv.minimal`.

Content comes from [TMDb Helper](https://github.com/jurialmunkey/plugin.video.themoviedb.helper)
(6.x) with a TMDb API key and a linked Trakt account. Without Trakt the Continue
Watching row hides itself and everything else still works.

## Screens

| Window | File | What it is |
| --- | --- | --- |
| Home | `xml/Home.xml` | Hero billboard, Continue Watching, a numbered Top 10, genre rows |
| Movies / TV Shows | `xml/Custom_114*.xml` | Generated browse pages |
| Search | `xml/Custom_1120.xml`, `Custom_1121.xml` | Titles, shows and people; 1121 is the twin used for a cast member |
| Title pages | `xml/Custom_113*.xml` | Five chained pages, so Back walks out the way you came in |
| Settings | `xml/Settings.xml`, `xml/SettingsCategory.xml` | Kodi's own settings, restyled |

## Generated files

Several windows are repetitive enough that they are written by a script. **Edit the
generator, not the XML** - the files carry a header saying so.

```bash
python3 tools/gen_textures.py .   # media/atv/*.png
python3 tools/gen_icon.py         # resources/icon.png, fanart.png
python3 tools/gen_rank.py         # the numbered Top 10 row
python3 tools/gen_browse.py       # Movies and TV Shows pages
python3 tools/gen_details.py      # the five title pages
python3 tools/gen_search.py       # the two search screens
```

`gen_browse.py` bakes today's date into its "new releases" windows, so re-run it
now and then to move that window forward.

## Kodi settings this skin expects

**Artwork resolution.** Kodi caches every downloaded image once, at `imageres`
(default 720) and `fanartres` (default 1080) - and never fetches a bigger one
later. On the defaults, posters are stored at 480x720 and backdrops at 1920x1080,
which are then upscaled on any display taller than that. The hero billboard is
where it shows most. Put this in `userdata/advancedsettings.xml`:

```xml
<advancedsettings>
    <imageres>1440</imageres>
    <fanartres>2160</fanartres>
</advancedsettings>
```

Existing cache entries keep their old size, so after adding the file clear the
texture cache (delete `userdata/Thumbnails/` and `userdata/Database/Textures13.db`
with Kodi closed) and let it rebuild.

TMDb Helper's own *Artwork quality* setting can stay on the default: it already
requests `w780` posters and `original` backdrops and logos, and the largest poster
this skin draws is 200x300 in a 1920x1080 coordinate space.

**Playback.** Two Kodi settings and one add-on setting decide whether a 4K Dolby
Vision stream is found and whether it plays well:

- *Settings > Player > Videos > Allow hardware acceleration - VTBDecoder* must be
  on, or 4K HEVC is decoded in software. It is on by default; check it if playback
  drops frames. With it on, `Player.Process(videodecoder)` reads `ff-hevc-vtb`.
- *Adjust display refresh rate* set to "On start/stop" matches the display to 24p
  content, the way an Apple TV does. It only does anything full-screen.
- Umbrella's *Terminate on Cloud Sources* should be **off**. With it on, a file
  already sitting in your Real-Debrid cloud ends the search immediately, so a 720p
  copy you grabbed once wins over the 4K releases that were never looked for.

**Sound, and what Dolby Vision actually does here.** Kodi only offers the audio
options the current output device supports. On a Mac driving its own speakers there
is no passthrough setting at all and 2.0 is correct - a 5.1 track is decoded in full
and downmixed. Connected to a TV or receiver over HDMI, pick that device under
*Settings > System > Audio*, set *Number of channels* to match it, and enable
passthrough for the formats it handles; only then does a DTS-HD MA or TrueHD track
leave the machine intact.

Dolby Vision is decoded here, not output. VideoToolbox handles the HEVC base layer,
so a DV release plays hardware-accelerated and looks right, but Kodi on macOS does
not emit DV metadata - that needs a player whose video path carries it end to end.
`VideoPlayer.HdrType` reporting `dolbyvision` means the file is DV, not that the
display is receiving it.

**Sources.** POV (with Magneto built in) is the default player, set in TMDb Helper as
`default_player_movies` / `default_player_episodes` = `pov.autoplay.json`. It replaced
Umbrella because Umbrella could not play whole classes of content: Indian and niche
titles are distributed as season packs whose release names say `S01`, and cocoscrapers
matches `S01E01` against that name, so it returned nothing at all. POV's scrapers
include the Real-Debrid cache indexes - DMM, Zilean, Torz, TorrentsDB, Bitmagnet -
which match filenames *inside* a pack.

POV settings that matter, all of which had to be changed from their defaults:

| Setting | Value | Why |
| --- | --- | --- |
| `filter.foreign.single.audio` | **false** | On, it discards releases whose only audio is non-English - which is most Hindi and Tamil content. |
| `autoplay_quality_movie` / `_episode` | `720p, 1080p, 4K` | SD was in the list, so an SD rip could win when nothing better was cached. |
| `provider.dmm`, `zilean`, `bitmagnet`, `torrentsdb`, `bitsearch`, `torrentdownload` | **true** | The debrid-cache indexes; off by default. |
| `auto_resume_movie` / `_episode` | `1` (Always) | Otherwise a resume prompt blocks playback. "Autoplay Only" does not work here: it checks POV's own `auto_play` setting, not the `autoplay=true` the skin passes in the URL. |
| `scrapers_timeout` | `20` | More providers need longer before the scrape is cut off. |

Umbrella is still installed and still in the Sources dialog, as is MediaFusion once you
give it a secret string. The **Sources** button on a title page lists all of them.

Measured after these changes: a fresh film resolves 4K Dolby Vision with DTS 5.1 in
about 7 seconds, and a Hindi title that Umbrella could not play at all now plays.

The `<cache>` block in `advancedsettings.xml` is what keeps a 14GB stream from
stalling; Kodi's default read-ahead is sized for local files.

## Testing

Kodi's JSON-RPC server on port 9090 drives the UI without touching the keyboard,
which is how the layouts here were checked. Kodi's own screenshot action is more
reliable than a screen capture, because it works when Kodi is on another Space:

```
{"jsonrpc":"2.0","id":1,"method":"Input.ExecuteAction","params":{"action":"screenshot"}}
```

Set `debug.screenshotpath` first to choose where they land.

> Never call `ControlEdit.getText()` or `setText()` on a skin edit control from a
> script - it segfaults Kodi 21. That is why search hands typing to Kodi's own
> keyboard dialog.
