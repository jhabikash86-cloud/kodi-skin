# Extra players for TMDb Helper

Copy these into

    userdata/addon_data/plugin.video.themoviedb.helper/players/

They are read at play time, and TMDb Helper ignores any whose add-on is not
installed, so copying them before installing POV is harmless.

`pov.*.json` were written from POV's own routing table
(`resources/lib/menus/movies.py`, `episodes.py`): POV takes a TMDb id and looks
the rest up itself, and `is_resolvable` is **false** because POV does not hand
a URL back: `POVPlayer.run()` calls `xbmc.Player().play()` itself. With `true`, TMDb
Helper waits for a resolved URL that never arrives and starts a second scrape, which
showed up as POV's progress dialog appearing twice. `autoplay=true` picks POV's best source without asking;
`autoplay=false` opens its source list.

Priorities are below Umbrella's (100/101) so Umbrella stays the default and
these show up underneath it in the Sources dialog.

MediaFusion ships its own player file and installs it from
*its* settings, under "Setup TMDb Helper" - no copying needed. It first needs a
secret string, which you generate on the MediaFusion site by entering your
debrid details there; that is a credential step, so it has to be done by hand.
