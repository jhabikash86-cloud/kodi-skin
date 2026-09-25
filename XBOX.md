# ATV Minimal on Xbox Series X + Samsung QN90A

The skin sets up the add-ons by itself (`extras/setup.py`). What it cannot do is install
them, sign in, or change the Xbox's and the TV's own settings. That is this page, in order.

Controller: **A** select · **B** back · **X** (or hold A) menu, where "Remove from this row"
is · **Y** full screen. While playing: A pause · B stop · X on-screen controls.

## 1. Kodi on the Xbox

- Kodi **21.x** (the Mac runs 21.3). A Kodi 22 refuses this skin.
- Kodi tile > ☰ > **Manage game and add-ons > File info > App type: Game**. In the default
  "App" mode the Xbox runs apps in a small, shared slice of memory and graphics - the main
  reason Kodi feels slow there. As a Game, Kodi gets the console's full resources. (Setting
  it to Game was ruled out as the cause of the network block: the block stayed with it off.)
- Kodi: Settings > System > Add-ons > **Unknown sources: On**.

## 2. Repositories - from the USB stick

Add-ons > Install from zip file > USB, one at a time, waiting for "Add-on installed":

| zip | gives you |
|---|---|
| `repository.umbrella-2.2.6.zip` | Umbrella, and the YouTube version the Mac uses |
| `repository.jurialmunkey-3.4.zip` | TMDb Helper 6.17 (Kodi's own repository only has 5.4) |
| `repository.kodifitzwell-0.0.1.zip` | Magneto, Umbrella's scraper |
| `repository.cocoscrapers-1.0.0.zip` | CocoScrapers |

## 3. Add-ons - Add-ons > Install from repository

- jurialmunkey > **TMDb Helper** (if 5.4 is already installed: My add-ons > TMDb Helper >
  Update, and pick the 6.x version)
- Umbrella repository > **Umbrella**, and **YouTube**
- kodifitzwell > **Magneto**
- CocoScrapers > **CocoScrapers**

Without Magneto and CocoScrapers Umbrella finds far fewer releases; that is why Furious
had no episodes on the Xbox.

## 4. The skin

Add-ons > Install from zip file > USB > `skin.appletv.minimal-0.3.2.zip`, then
Settings > Interface > Skin > ATV Minimal. **Quit Kodi and open it again** (Xbox button >
Kodi > ☰ > Quit). A notice lists what it set up.

## 5. Sign in - the only settings to do by hand

- **TMDb Helper**: Trakt (Authorize - enter the code at trakt.tv/activate)
- **Umbrella** > Accounts: Trakt; Real-Debrid and AllDebrid (both are signed in on the Mac);
  Easynews; OpenSubtitles (a free opensubtitles.com account, for subtitles)
- **Magneto**: the AIOStreams username and password (the Mac has them set)

Quit and reopen Kodi once more.

## 6. The Xbox - Settings > General > TV & display options

- Resolution **4K UHD**, refresh rate **60 Hz**
- Video modes: **Allow 4K** on · **Allow HDR10** on · **Allow 24 Hz** on (films play at
  their own frame rate; the skin turns on Kodi's matching) · **Allow 50 Hz** on ·
  **Allow variable refresh rate** off (it upsets video, not games) · **Allow auto low-latency
  mode** on · Dolby Vision off (the QN90A has none)
- Colour depth **10 bits per pixel**; colour space **Standard**
- Power options: **Sleep**, so Kodi is there in seconds

## 7. The TV - on the Xbox's HDMI input

- Settings > Connection > External Device Manager > **Input Signal Plus: On** for the
  Xbox's port - without it the TV takes no 4K 60 HDR signal.
- **Game Mode: Auto**. With Kodi as a Game and auto low-latency on, the TV switches to Game
  Mode while Kodi runs: the controller responds in about 10 ms instead of a noticeable delay,
  which is most of the "Apple TV" snap. Films then play with the TV's lighter Game Mode
  processing; if you would rather have Filmmaker Mode for films, set Game Mode off and
  accept a slower-feeling remote.
- **Game Motion Plus: Off**, and outside Game Mode **Picture Clarity: Off** - no motion
  smoothing on films.

## 8. First run

The first visit to each page fetches everything once; after that it comes from the Xbox's
cache. Open each tab once, rest on a few titles, and it is quick from then on. Rows load as
you reach them, so the two on screen never wait behind the ones below.

If a row shows "Nothing here yet" or a title will not play, send the address from
**Kodi Log Uploader** (Kodi's repository > Program add-ons) - it shows exactly what failed.
