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
python3 tools/gen_search.py .     # the two search screens
```

Rows never go stale. Where a row has a date window - "In Cinemas Now" is the last 45 days,
the charts the last 18 months, "of the Decade" the last ten years - the XML asks for
`$INFO[Window(home).Property(ATVDate.d45)]` and `extras/dates.py` sets it: from
`Startup.xml`, before Home builds a row, and again each minute from `extras/prefetch.py`, so
after midnight the windows move on by themselves and the rows reload. Nothing needs
regenerating.

## Setting up a new device

Install the skin, install TMDb Helper, Umbrella, YouTube and Magneto from the same
repositories as the Mac, restart Kodi once, and sign in (Trakt, debrid, Easynews,
AIOStreams). The rest is done by `extras/setup.py`, which runs at every start from
`Startup.xml` and, for each of those add-ons it finds, applies once what is below: Play
opening Umbrella's source list (and the two player files); Umbrella's scraper, filter,
subtitle and Trakt settings, with Magneto as its external scraper once Magneto is
installed (Umbrella takes one; it needs both the add-on id and the module name, `magneto`);
the providers Magneto has switched on; English subtitles;
YouTube's server for trailers; and an `advancedsettings.xml` where there is none (the
Xbox-safe one in `extras/`). On the Xbox it also picks lighter posters (w780 rather than
2000x3000 originals) and turns on matching the TV to the film's frame rate. Settings are
applied once per add-on and then left alone, so changing one later sticks; an add-on
installed later is set up at the next start. It also applies three fixes to TMDb Helper's
shared module whenever it finds the module without them - after an update, the next start
fixes it again - and only where the lines it replaces are exactly as expected. Nothing
touches an account. Without Magneto, Umbrella found no releases at all for some new shows
on the Xbox (Furious). CocoScrapers is installed on the Mac but unused - Umbrella points at
Magneto - so the Xbox does not need it. Tested on the Mac by reverting every one of these
settings, removing the players and the fixes, and starting Kodi: all came back, and Play
opened the source list.

## Kodi settings this skin expects

**Artwork resolution.** Posters come from TMDb at their original size - 2000x3000 for
most recent titles, though some are barely larger than the 780px copy TMDb also
offers - with TMDb Helper's *Artwork quality* set to the last option (`artwork_quality`
4). That option changes posters only; backdrops, logos and thumbs are original on
every setting.

More pixels were not what made posters look soft. Kodi keeps one resized copy of each
image and draws it by stretching that copy on the GPU with a plain bilinear filter, so
a 1170px copy drawn at 600px came out visibly softer than the same file downscaled
properly. The fix is to make the cached copy close to its drawn size, from the full
original, with a good filter - in `userdata/advancedsettings.xml`:

```xml
<advancedsettings>
    <imageres>1080</imageres>          <!-- above a focused poster on a 4K screen (~810) -->
    <fanartres>2160</fanartres>        <!-- backdrops stay 4K -->
    <imagescalingalgorithm>lanczos</imagescalingalgorithm>
    <imagequalityjpeg>2</imagequalityjpeg>   <!-- lower is better -->
</advancedsettings>
```

Compared on the same poster at the same drawn size, the result is clearly sharper:
rain specks are points rather than smudges, and hair and beard read as texture. It
uses no more memory than before (720x1080 against 780x1170). The cost is the first
time a poster is seen - a 1-3MB original to fetch and resize, about a second for a
page of them, covered by the loading placeholders - and never again after that.

Existing cache entries keep their old size. To rebuild them, delete
`userdata/Thumbnails/` and `userdata/Database/Textures13.db` with Kodi closed.

**The window shape.** Kodi stretches the skin's 1920x1080 to fill its window. A
windowed Kodi on a Mac is rarely 16:9 - measured here at 2886x1754, 1.645:1 - so every
poster and every letter was about 8% taller than drawn. Run Kodi full screen, or on a
16:9 display, and it goes away.

**Subtitles.** English by default. Kodi's *preferred subtitle language*
(`locale.subtitlelanguage`) is English - it was "original", which in practice meant off - so
any English track in the file comes on by itself; Kabali (Tamil) played with its English
track on. Umbrella's own subtitles are on, English, preferring the file's own track: when
the file has none it downloads the best match from OpenSubtitles. That last part needs a
free OpenSubtitles.com account, entered in Umbrella's settings (Accounts -> OpenSubtitles:
username, password, then *Test*); without one, embedded tracks still work and Umbrella says
it is not authorised when it would have downloaded.

**Resuming.** Nothing asks "Resume from ... / Play from beginning". `extras/play.py` plays
with `noresume`, because Kodi keeps its own bookmark for the plugin link and asked before
the source list could even open; the resume point comes from Trakt and is applied once the
stream is up. Umbrella's *Auto Resume* is on for the same reason.

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

**Sources.** Umbrella (with Magneto as its external provider) is the player, set in
TMDb Helper as `default_player_movies` / `default_player_episodes` =
`umbrella.select.json`. Pressing Play scrapes and then lists every release it found -
quality, size, which debrid service holds it, which scraper found it - and you choose.
POV is installed but disabled; its player files are still in the players folder.

The player files are not shipped by either add-on. They live in `extras/players/` and
are copied to
`userdata/addon_data/plugin.video.themoviedb.helper/players/`. `select=0` in the URL is
Source Select, `select=1` is Auto Play. Keep the copy in `extras/players/`: deleting the
installed ones leaves Play pointing at a player that no longer exists, and nothing in
either add-on puts them back.

Umbrella settings that matter:

| Setting | Value | Why |
| --- | --- | --- |
| `sources.sort.order` | `1` (Quality, Size, Provider) | Left at the sensible value; changing it did not reorder the list - see **Ordering** below. |
| `remove.sd.sources` | **true** | Drops anything below 720p, but only when something better exists, so it cannot empty the list. |
| `remove.cam.sources` | **true** | Cams are never the best copy of anything. |
| `hosts.quality` | `0` (4K) | The ceiling, not the floor. |
| `scrapers.timeout` | `20` | Was 60. This is the ceiling on a cold scrape and it was most of the wait. |
| `preemptive.termination.movie` / `.tv` | **true** | Stop scraping once there is enough to choose from instead of always running to the timeout. |
| `preemptive.res.movie` / `.tv` | `0` (4K) | Only stop early on 4K results. Stopping early on 1080p would be faster still, but it can end the scrape before a 4K release arrives from a slower scraper. |
| `preemptive.limit.movie` / `.tv` | `10` | Ten 4K sources is more than anyone picks from. |
| `source.filtermbysize` | `0` (Off) | Leave it off. On, `source.max.moviesize` caps at 10GB, which excludes every 4K remux. |
| `terminate.onCloud.sources` | **false** | On, a cloud source ends the scrape and a 720p can win. |

On timing: the first scrape of a session took **11.7s**; every cold scrape measured
afterwards - cache emptied each time from `providers.db`, table `rel_src`, with Kodi shut
down - came back in **0.6-2.1s**, across Kabali, Animal and Vikram, and stayed under a
second even with the pre-emptive settings turned back off. So most of that first 11.7s
was session start-up, not the scrapers, and the speed here is not something these
settings bought. What `scrapers.timeout` does buy is the bad case: a scrape that stalls
now gives up after 20s instead of 60. Umbrella also caches a title's sources for
`cache.providers` hours, 48 by default, so a second Play on the same title is instant.

**Ordering.** Changing `sources.sort.order` did not change the Source Select list in
Umbrella 6.7.87. Setting it to `4` (Size, Quality, Provider), which should put the largest file
first, produced a byte-identical list to `1` on a cold cache. What the list actually
shows is scraper arrival order - MediaFusion, then Comet, then Torrentio - each group
internally ordered. So Vikram lists two 4K/27.71GB, then four 1080p/2.2-2.8GB, then two
4K/29.28GB: the biggest 4K release sits at row 7, below four 1080p files.

The sort itself does run - `sourcesFilter` in `sources.py` orders by the setting, and
nothing after it regroups by provider - so the likelier cause is that some scrapers' rows
carry a size or quality the sort reads differently from the badge the list draws. That is
not confirmed; what is measured is the list above.

**Settings -> Play** switches between "ask me which source" (Source Select, the default)
and "pick the best automatically", which sends the same press to Umbrella's Auto Play
(`umbrella.autoplay.json`, via TMDb Helper's `player=` and `mode=play` parameters). Auto
Play starts the top source and falls through to the next if it will not play.

An earlier version did the automatic pick itself, reading Torrentio with your debrid keys
(`extras/resolve.py`, now removed). It could not work. For Kabali, 23 of the 24 copies
Torrentio listed as cached on Real-Debrid were not playable - 8 were not cached at all
(Real-Debrid began downloading them), 7 failed, 5 had been taken down for copyright, 3
timed out - and every AllDebrid link came back `blocked_access`: AllDebrid refuses
Torrentio's servers. The only copy that played was a Latin-American Spanish dub. A
debrid refusal still streams, as a short explainer clip under the release's own file
name, so it looks like a film that will not start. Umbrella checks sources itself and
talks to both services from this machine, which is why its list plays.

**Duplicates.** The same release appears once per debrid service - one AllDebrid row and
one Real-Debrid row, next to each other, same name and size. `remove.duplicates` is on
and does not collapse these: `filter_dupes` in Umbrella's `sources.py` matches on magnet
hash or on an identical URL, and the same torrent resolved through two services has
neither. There is no setting for it. Dropping a service would halve the list at the cost
of everything only that service has cached.

**Titles that share a name.** Six films are called *Animal*. extras/play.py warns when
the release name does not read like the title asked for - the French *Le Regne Animal*
in place of the Hindi *Animal* - and only warns, because getting it wrong must never
cost a film that would have played. With the picker in front of you this matters less
than it did under autoplay.

**What the list says is not always what opens.** Kabali's top row read
`1080p ... H264, 10.11 GB`; the stream that opened was HEVC. The name in the list is the
torrent's name, and the file a debrid service hands back does not have to match it.
Treat the quality badge as a strong hint, not a guarantee.

**Availability.** An earlier version of this file said older Tamil and Hindi titles
often have no cached copy and that Play therefore could not succeed. That was wrong.
Probing Real-Debrid and AllDebrid directly for ten titles - Kabali, Sivaji, Baasha,
Enthiran, Muthu, Padayappa, Animal, Jawan, Tumbbad, Vikram - every one had cached,
playable releases, from 3 for Padayappa to 50 for Kabali. When one of these would not
play, the cause was the player, not the catalogue.

Traps the picker will show you, all seen in the ten titles above: a 120GB pack of 75
films, `South.Indian.Movies.Pack`, Russian dubs of Jawan and Tumbbad, a songs
compilation returned for Enthiran, a "4KRM" release group tag on a 1080p Muthu, and a
"DVD Upscale" labelled 1080p for Padayappa. Muthu was the one title of the ten that did
not play from its top source, and a pack was what sat there.

The `<cache>` block in `advancedsettings.xml` is what keeps a 14GB stream from
stalling; Kodi's default read-ahead is sized for local files.

## Why pages went blank - and the fixes outside the skin

Pages that stayed black, a title page with a "TMDb Helper" error, and one Kodi session where
nothing loaded at all had one cause. From this network, **TMDb's API cannot be reached over
IPv6** - six attempts, six timeouts - while IPv4 answers in 0.15s; every other service works
on both. Browsers and curl try both at once, so nothing else noticed. Kodi's Python tries IPv6
first and waits out the timeout, so any TMDb request not already cached could hang - and
while it hung it held TMDb Helper's lock on that title, which every other list about the title
waits on. Past that lock's 10s limit TMDb Helper crashed on a bug in its own timeout message,
and the row came back empty. Kodi's remote-control server has one thread, so a hung request
also froze the remote and everything behind it.

Changes in `script.module.jurialmunkey` (TMDb Helper's shared module) fix it, each marked
`skin.appletv.minimal` in the file and recorded in `extras/patches/`:

- `reqapi.py` - its requests use IPv4 only (`urllib3.util.connection.HAS_IPV6 = False`).
- `locker.py` - a lock timeout no longer crashes the request; it carries on without the lock.
- `bcache.py` - a list that failed (no items and no pages; TMDb always answers with at least
  one page) is no longer cached. TMDb Helper kept every answer six hours, failures included,
  so one stalled request left its row empty for the rest of the evening. The first start
  with this fix found 35 such rows cached on the Mac, and clears them (`extras/setup.py`).

An update of that module replaces both, which is one reason Kodi's add-on updates are set to
*Notify, but don't install updates* (Settings > System > Add-ons). The lasting fix is on the
network: IPv6 to TMDb's servers is broken on this connection - worth raising with the ISP, or
turning IPv6 off on the router.

The title page also asks in order now. It used to open six lists about the same title at once
- details, seasons, episodes, cast, More Like This, You May Also Like - and each fetched the
title's details again for itself, queueing on the lock. Now the details come first, alone, and
the rest follow and read them from the cache (`ATV_DetailReady`). Measured afterwards: every
part of a page loaded, including a soap with 38 seasons and 195 episodes, with no lock timeout.

## How pages load

Measured on this skin, a TMDb Helper listing takes 0.7-1.5s the first time and
0.05-0.3s once cached; a title's details take about 1.4s. Everything below is about
paying that before you notice it.

**Rows load as you reach them.** Every listing is a Python run of TMDb Helper, and a page
used to start them all at once - twelve on Home, seventeen on Movies - so on the Xbox the
two rows on screen queued behind fifteen you could not see. Now the first three rows of a
page load straight away and each row below exists, and so loads, only once the focus is
within two rows of it (`lazy()` in `tools/gen_home.py` and `tools/gen_browse.py`); a row
Kodi does not draw asks for nothing. Scrolled down Home, every row was full before it
came on screen.

**Fetching ahead** (`extras/prefetch.py`, started with Home). A few seconds after
startup it walks every row of the Movies and TV pages and the Home hero's titles, so the
first visit to either page is as quick as the second; it walks them again every three
hours, as TMDb Helper's caches expire. And when you rest on any title for a third of a
second, it fetches that title's details and "You May Also Like" at once - only the one
you are on, never a queue of titles scrolled past. A title rested on for two seconds
opened fully in 0.25s, against 1.55s for one selected straight away.

**Title pages never show the previous title.** Kodi keeps a page's last listing in
memory and shows it until the new one arrives, so opening a film used to show the last
film's backdrop, plot and recommendations for a second or more. Now `extras/details.py`
copies the clicked tile's backdrop, logo and title across before the page opens, so it
opens on the right picture in 0.1s; the plot and credits wait until the details
listing's own TMDb id matches (`ATV_DetailReady§`); and each row stays hidden, showing
placeholders, while `Container(id).IsUpdating` says it still holds someone else's items
(the `stale` parameter of `ATV_PosterRow`).

**More Like This** is built from the title's own details, not from the tile you
clicked, which can carry only its first genre: a Comedy / Horror / Romance film arrived
as "Comedy" and the row filled with Toy Story and PAW Patrol. Same genres and language,
then held to a standard - films popular, from the last twenty years, with a vote floor;
shows by rating over the last twelve years, without soap, talk, reality, news or kids
formats. The Gentlemen now leads to Brassic, Inside No. 9 and Barry rather than Monk,
Psych and Rizzoli & Isles.

## What rows show

Rows are for things you can watch now: every one passes `hide_unaired=true`, which drops
titles not out yet - they otherwise appeared with TMDb Helper's red italic markup in their
names. Coming Soon, My List and Continue Watching keep them.

**Continue Watching** is two rows: the episodes you paused, then the films, each Trakt's
on-deck list, newest first. Anything under 4% watched is left out (TMDb Helper already
zeroes progress below that), which drops false starts, and so is anything not played in 90
days: Trakt keeps a paused position forever, and this account had 40. A show with two
paused episodes still shows both.

To take a tile off by hand, press Menu on it: the first entry, *Remove from this row*, runs
`extras/forget.py`, which deletes that saved position on Trakt through TMDb Helper (the title
is not marked watched), closes TMDb Helper's "successful" box and reloads both rows - about
three seconds. A failure leaves TMDb Helper's box up, since it says why; a tile Trakt still
lists after two reloads gets a "try again" notice. Trakt once answered a delete with success
and kept the entry; the same delete sent again went through.

They were one row for a day - two `<content>` lists in one container, which Kodi 21 merges -
and it froze Kodi. Its multi-list provider takes a list's lock while holding the graphics
lock; a list that has just finished loading holds its own lock while freeing the old
artwork, which needs the graphics lock. Each waits for the other, and everything stops: the
remote, the pages, even Quit. A row with one list does not take that path, so every row in
the skin has one list. Checked afterwards with five cold starts in a row.

**Genre rows** are thrillers, horror and dramas only - what this house watches; the comedy
and sci-fi rows are gone. Two kinds, `everyone_watching()` and `must_watch()` in
`tools/gen_browse.py`:

- *Thrillers Everyone's Watching*, *Horror Everyone's Talking About* and *Dramas Everyone's
  Hooked On*, on Movies and TV: Trakt's weekly chart of unique viewers, cut to the genre and
  to titles Trakt members rate well - IMDb too, for films. Films are held to the last three
  years (`ATVDate.y3`, kept current by `extras/dates.py`) so the row is what is new; a series
  binged this week counts however old it is.
- *Must-Watch Thrillers: The All-Time Greats*, *Must-Watch Horror: Lights On*, *Must-Watch
  Dramas: The Classics* and *Must-Watch Drama Series*: TMDb, thousands of votes, best rated
  first - The Dark Knight and Se7en, Psycho and The Shining, Shawshank and The Godfather,
  Breaking Bad and Chernobyl.

Cartoons and comedies are left out of all of them, horror out of the thrillers, thrillers out
of the dramas (five of the twenty drama greats were also thriller greats), musicals out of
the film dramas. Trakt's own all-time list was tried for Must-Watch and dropped: filtered to a
genre it returned five to thirteen titles, nearly all from this year. Trakt ignores its vote
filter on these charts; the rating filters work. Gripping Crime Dramas and Bollywood Romance
stay from the earlier mood rows.

*Top 10 Most Watched This Week* on Movies is Trakt's weekly chart of unique viewers
(`trakt_mostviewers`). It used `trakt_mostwatched`, which despite the name is your own
history by play count - it showed the films you had rewatched.

**My List** is its own tab: your Trakt watchlist, which is what the My List buttons add to,
films and shows, newest first, upcoming titles included.

**More Like This** for a title TMDb knows little about falls back to TMDb's "similar" list;
a row that loads with nothing in it says "Nothing here yet" instead of pulsing placeholders.
A show that is announced but not aired says "Episodes aren't out yet" with its premiere date.

*In Cinemas Now* and the Home hero are films that opened in the last six weeks with at
least 20 votes. TMDb's own now_playing list carries re-releases, so *Avengers: Endgame*
(2019) was in cinemas; filtering by the Indian region was worse, surfacing La La Land.

**Search** drops results with a TMDb popularity under 1. "shahrukh khan" listed three
empty profiles before the real Shah Rukh Khan and fan-made DVDs before his films; now
it is the star and his Netflix special. Upcoming films are kept, being popular long
before they have votes. TMDb Helper compares the value as text, which is only safe
because the threshold is 1.

**The hero trailer** starts after four seconds still on the hero - on its buttons or on the
tab bar above it, since coming back to Home through the tab bar leaves focus there with the
whole hero in view. Measured from the request to the picture: about 3-4s when YouTube is
quick. *Settings -> Banner trailers* turns them off.

While the YouTube add-on looks a trailer up, Kodi shows a modal busy dialog that ignores
every key but Back, and nothing in Kodi's settings changes that (`busydialogdelayms` and
`videobusydialogdelayms` were both tried and did not). So the pause is four seconds, not
two, to keep lookups to when you have stopped browsing; and a key pressed during a lookup
cancels it, so the next press reaches Home at once instead of up to 40s later. The press
that cancels it is lost - Kodi gives a skin no way to hand it on.

Most of the wait is the YouTube add-on looking the video up, which measured anywhere from
2s to 31s, and got slower the more trailers were asked for - YouTube throttling it. Three
things follow from that:

- `extras/trailer.py` gives a trailer 40s to start. At 10s it used to give up, the hero
  moved on, and the trailer then arrived late, for a title no longer shown, playing as
  sound with its picture hidden. That was the long-standing "trailer plays only the sound".
- A YouTube stream that turns up after the preview was stopped or given up on is stopped,
  once - Kodi can block for a minute closing a stream that is still opening, so it is never
  asked twice. A trailer that never starts is skipped for the rest of the session.
- In the YouTube add-on, *MPEG-DASH stream features* no longer include AV1, HDR, 3D and VR
  (`kodion.mpd.stream.features`). It had been choosing AV1, which a Mac decodes in software;
  H.264 and VP9 start faster and look the same at this size. Leave *listen address*
  (`kodion.http.listen`) at `0.0.0.0`: set to 127.0.0.1 it still hands the player the
  machine's network address, the connection is refused, and every trailer fails. Its
  "Failed to connect" log lines are harmless - it falls back at once.

Only a widescreen trailer is ever shown. Studios post square and vertical social cuts under
the same "Trailer" label, often with captions burned in; after 1s of playback the aspect is
checked, anything narrower than 1.6:1 is stopped and never tried again, and Home shows the
video only once it has passed.

## Playback details that were quietly broken

- **Starting anything from Home stopped it.** Home's `<onunload>` ran `Action(Stop)` to end a
  trailer when you leave Home - but playback switches to full-screen video, which unloads
  Home, so an episode started from Continue Watching stopped 0.7s after its first frame.
  It now only stops the player while a trailer preview is showing.
- **TMDb Helper plays a placeholder first.** With a resolvable player like Umbrella it plays
  `dummy.mp4` and swaps the stream in once resolved. `extras/play.py` took the placeholder
  for playback, saw it end, and gave up before resuming - Continue Watching always started
  from 0:00. It now waits for the real stream, and does not count time spent in the source
  list against its timeout.
- **Up Next never appeared, and could not have worked.** `extras/upnext.py` started before
  the stream resolved and quit a second later, seeing nothing playing. The card was also a
  plain window, not a dialog, so it replaced the picture with black and could not be closed.
  And the countdown led nowhere: when the episode ended, nothing played. Now it waits for the
  episode, overlays it, and when the episode ends with the card still up, the next one starts
  on Auto Play - nobody is at the remote to choose a source. Pressing its Play button follows
  your Play setting.
- **Backing out of the source list** left `extras/play.py` waiting up to three minutes for a
  stream that was never coming, with the hero's trailers switched off the whole time. The
  wait (`extras/waiting.py`, shared with `upnext.py`) now pauses while the list is open and
  gives up 10s after it closes with nothing playing.
- **Quitting Kodi** could freeze it. Kodi only asks a skin's scripts to stop after it has
  unloaded the skin, when their GUI calls wait on a Kodi busy shutting down; it killed them
  after 5s each and sometimes never finished exiting - reliably when a trailer was loading.
  `extras/trailer.py` and `extras/prefetch.py` now leave on `System.OnQuit`, at the start of
  shutdown: quitting takes 3-6s in every state, with nothing killed.
- **Download subtitle looked frozen.** With no subtitle add-on installed it opened a window with nothing in
  it to select - on a controller it looked frozen over the paused video. It now offers
  *Get a subtitle add-on*, which opens Kodi's list of them (OpenSubtitles.com is one; it
  needs a free account).
- **Stop a trailer, then Quit, froze the quit.** It held Kodi for minutes: Home
  restarted the trailer watcher after Kodi had announced it was quitting, and that script,
  never hearing it, blocked the shutdown. The first script to hear the quit now marks Home
  (`ATVQuitting`), Home starts no script once marked, and one that starts anyway leaves at
  once (`extras/waiting.py`). The same stop-then-quit now exits in 6 seconds.

## The look

- **Focus.** A focused poster comes forward, as on Apple TV: 14% larger (12% on Top 10
  rows), lifted a few pixels, over a deeper shadow, with a thin light edge. It grows from a
  point a third of the way down, so it never reaches the row title above. (A sheen across the
  poster was tried and removed.)
- **Top 10** numerals are outlined, Netflix style, and sit behind their posters. Only the
  poster lifts on focus; when the whole tile scaled, the numeral swung across the poster
  to its left.
- **Glass.** Kodi has no live blur, and TMDb Helper's blur service would download and
  blur a full-size backdrop on every focus change. The tab bar and the unfocused buttons
  get what actually makes glass read as glass instead: light on the top edge and a
  bright hairline round the rim.
- **Billboards scroll away.** Moving into Home's rows carries the hero's text up with the
  page - the same distance, time and curve as the rows' first step - while its backdrop
  drifts up more slowly behind and fades. On Movies and TV the first row is backed by the
  backdrop of whatever has focus in it, the page's billboard; below that the page is plain
  dark, because behind every row the backdrop competed with the posters and hid the glass
  and focus effects.
- **The tab bar stays out of the way.** It shows only while it has focus: press Up at the
  top of a page, or Back. Back climbs as on Apple TV - from a row to the top of the page,
  from there to the bar (on the tab of the page you are on), and from the bar to Home. On
  Movies and TV each Back names a control rather than running `SetFocus()`: Kodi treats a
  control id as a move and stops, but after a command it still runs the page's own Back,
  which left the page. On Top 10 rows Back sits on each tile, since the focus is on the
  tile, not the row around it.
- **Trailers play full-screen.** Two and a half seconds into a hero trailer the shades, the
  hero's text and buttons and the rows below fade away (`ATV_TrailerFull`), over black, so a
  trailer wider than the screen is letterboxed rather than framed by strips of the still
  backdrop. The first press stops it and brings everything back; the next goes on as usual.
- Every hero button has an icon and a left-aligned label. A button needs its text offset
  on both sides, so "More Info" with an icon needs 290 wide.

## On the Xbox - what testing there found

Everything here was measured on the Xbox Series X itself, through a small test add-on that
connects out to the Mac (the Xbox blocks connections coming in): key presses, info labels,
screenshots, Kodi's log, and Python run inside Kodi there. Kodi 21.2, Python 3.8, SQLite
3.30, all eight cores and 3.3 GB free to Kodi.

**Why it was slow.**
- Every TMDb Helper call costs about 0.7s on the Xbox before it does anything - starting
  Python and importing the add-on - against 0.05s on the Mac. Keeping its Python running
  between calls (`reuselanguageinvoker`) crashed Kodi on the Mac when rows loaded in
  parallel, which is presumably why TMDb Helper ships with it off. So: fewer calls, made
  earlier. Rows load as you reach them; nothing starts with Home that can wait.
- TMDb Helper's details cache never worked there: SQLite 3.30 rejects two of its statements
  ("SQL logic error", 143 in an evening), so no title's details, cast or art were saved and
  every title page was fetched again. `extras/setup.py` patches both (on an SQLite older than
  3.35 only) - see "three fixes" above, and `HELPER_FIXES`.
- At a cold start about fifteen Python processes began in the same second and slowed each
  other: Home opened at 1.0s but its first rows filled at 6.7-14s. Now only what is on
  screen loads first: setup runs at start only after a skin update, the date windows and
  the hero are remembered between runs, prefetch and the trailer watcher start seconds
  later, and TMDb Helper trusts an unexpired Trakt token instead of confirming it with
  Trakt (1.6-2.2s at every start). Eight add-on services from other setups (Fen Light, POV,
  Embuary, Umbrestuary, script.trakt, service.upnext, CocoScrapers) and Kodi's version check
  were switched off.
- Once loaded, pages are quick: a tab switch draws completely in 0.1-0.5s, a key press
  moves focus in about 0.1s, the GUI holds 60fps.

**Why playback stopped, stuttered or felt soft.**
- Kodi's stream buffer was 20 MB - two seconds of a remux. Kodi 21 reads it from its own
  settings (`filecache.memorysize`), not from advancedsettings.xml, so the 100 MB set there
  never applied anywhere. Now 256 MB; a 2s stall from the debrid server during an episode
  later passed unnoticed. The Xbox pulls 229 Mbit/s from the debrid service.
- At 120Hz Kodi presents at 60fps, so 24fps film ran 3:2 - judder on every pan. Frame-rate
  matching is on, with 2s for the TV to settle; without it the switch collided with the
  HDR switch and the renderer failed and retried.
- F1's list was topped by a 78 GB full Blu-ray disc image, which Kodi plays badly over the
  internet; an AI upscale was fifth. Both are filtered out now (a patch to Umbrella, and its
  own AI filter). Episodes are held to 1-10 GB (season packs, listed at 15-40 GB, drop out),
  films to 3-100 GB; Umbrella no longer puts Dolby Vision first (the QN90A has none).
- Up Next quit Kodi: the next episode was asked for while the last still played, and Kodi
  exits on "two concurrent busydialogs". It now stops the episode first. The card counts
  down ten seconds; its Play button starts the next at once; both Auto Play.

**Found, not fixed.** The hand-over to the next episode takes about 40s - Umbrella's search
(11-22s) and the HDR and refresh switches. Umbrella pre-scrapes the next episode only for its
own playlists. Real-Debrid and AllDebrid no longer let apps check what is cached, so every
release shows as UNCHECKED; seeders are no substitute (the cached-release indexes report 0).

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
