"""Generate the Movies (1140) and TV Shows (1141) pages.

Run from the skin folder:  python3 tools/gen_browse.py

Each page is the shared tab bar, a page title and a list of rows. Rows are either a
normal poster row or a numbered Top 10 row (tools/gen_rank.py). Geometry, the
step-based page scroll and the bottom stop are all worked out from ROWS below, so
adding a row is one line - the rest follows.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = 'plugin://plugin.video.themoviedb.helper/?'

FIRST_ROW_TOP = 260
ROW_STRIDE = 475
ROW_HEIGHT = 455          # a row's content, used for the bottom stop
SCREEN_BOTTOM = 1040      # leave a margin under the last row
HEADER_TOP = 150          # where the focused row's title settles

# Rows should show what is current, not all-time favourites. Trakt's trending and
# most-watched lists are "what people are playing right now"; for the language rows TMDb
# has no such list, so they use popularity limited to recent releases. Re-run this
# generator now and then to move that window forward.
# Date windows are filled in by Kodi from extras/dates.py, so rows never go stale.
DATE = {n: f'$INFO[Skin.String(ATVDate.{n})]' for n in ('today', 'd45', 'd90', 'd365', 'd540', 'd1095', 'd3650', 'y3')}
RECENT_SINCE = DATE['d540']
NEW_SINCE = DATE['d90']
YEAR_SINCE = DATE['d365']
THREE_YEARS = DATE['d1095']

# TMDb genre ids for the formats that dominate Indian popularity but are not what anyone
# means by a "top 10": soap, news, talk, reality, kids.
NOT_SERIALS = '10766,10763,10767,10764,10762'

DECADE = DATE['d3650']   # "of the decade": the last ten years
TODAY_ISO = DATE['today']

# TMDb records nothing about release resolution, so there is no way to ask it for 4K
# titles. This row is the closest honest proxy - big, heavily voted, already released -
# and in practice those all have UHD releases. It is not called a 4K row because the
# query cannot actually promise that; the resolution of what you get is decided by the
# source POV picks, and it shows it.
BLOCKBUSTERS = (f'{PLUGIN}info=discover&amp;tmdb_type=movie&amp;sort_by=popularity.desc'
                f'&amp;primary_release_date.gte={DECADE}&amp;primary_release_date.lte={TODAY_ISO}'
                f'&amp;vote_count.gte=2000&amp;nextpage=false')

WORLD_MOVIES = (f'{PLUGIN}info=discover&amp;tmdb_type=movie&amp;with_origin_country=KR%7CJP%7CFR%7CES%7CIT'
                f'&amp;sort_by=popularity.desc&amp;primary_release_date.gte={RECENT_SINCE}'
                f'&amp;vote_count.gte=30&amp;nextpage=false')

WORLD_SHOWS = (f'{PLUGIN}info=discover&amp;tmdb_type=tv&amp;with_origin_country=KR%7CES%7CFR%7CIT%7CDE'
               f'&amp;sort_by=popularity.desc&amp;first_air_date.gte={THREE_YEARS}'
               f'&amp;without_genres={NOT_SERIALS},16&amp;with_id=True&amp;vote_count.gte=20&amp;nextpage=false')


def language_chart(code, media='movie', votes=15, recent=True):
    """A language's current chart.

    Small catalogues (Tamil television, for one) do not have enough titles inside a
    recency window to fill ten tiles, so `recent=False` drops it and lets popularity
    alone decide.
    """
    date_key = 'primary_release_date' if media == 'movie' else 'first_air_date'
    since = RECENT_SINCE if media == 'movie' else THREE_YEARS
    window = f'&amp;{date_key}.gte={since}' if recent else ''
    extra = '' if media == 'movie' else f'&amp;without_genres={NOT_SERIALS}&amp;with_id=True'
    return (f'{PLUGIN}info=discover&amp;tmdb_type={media}&amp;with_original_language={code}'
            f'&amp;sort_by=popularity.desc{window}{extra}'
            f'&amp;vote_count.gte={votes}&amp;nextpage=false')


def best_of_language(code, media='movie', votes=120):
    """Highest rated of a language since DECADE - the "of the decade" rows."""
    date_key = 'primary_release_date' if media == 'movie' else 'first_air_date'
    return (f'{PLUGIN}info=discover&amp;tmdb_type={media}&amp;with_original_language={code}'
            f'&amp;sort_by=vote_average.desc&amp;{date_key}.gte={DECADE}'
            f'&amp;vote_count.gte={votes}&amp;nextpage=false')


def network(network_id, votes=20):
    """A network's chart: recent titles it originated, most popular first."""
    return (f'{PLUGIN}info=discover&amp;tmdb_type=tv&amp;with_networks={network_id}'
            f'&amp;sort_by=popularity.desc&amp;first_air_date.gte={THREE_YEARS}'
            f'&amp;vote_count.gte={votes}&amp;nextpage=false')
TODAY = DATE['today']

# Every row should pull a different slice. Sorting everything by popularity made the same
# half-dozen blockbusters fill the Top 10, Popular, In Cinemas and the genre rows, so the
# page read as one list repeated. Now: what is hot, what is new, what is on, what is
# coming, and the best of a genre by rating - which surfaces a completely different set.
# TMDb's now_playing carries re-releases - Avengers: Endgame (2019) was "in cinemas" - so this
# is films that opened in the last six weeks, held to a vote floor so festival one-offs
# stay out. By region it was worse: an India filter surfaced La La Land and Train to Busan.
CINEMA_SINCE = DATE['d45']
IN_CINEMAS = (f'{PLUGIN}info=discover&amp;tmdb_type=movie&amp;primary_release_date.gte={CINEMA_SINCE}'
              f'&amp;primary_release_date.lte={TODAY}&amp;sort_by=popularity.desc'
              f'&amp;vote_count.gte=20&amp;nextpage=false')

# Genre rows, for thrillers, horror and dramas only - what this house watches. Two kinds:
#
#   Everyone's Watching - Trakt's weekly chart of unique viewers, cut to the genre and to
#   titles its members rate well (and IMDb too, for films). Films are held to the last three
#   years, so the row is what is new and talked about; a series binged this week counts
#   however old it is.
#   Must-Watch - the all-time greats: TMDb, thousands of votes, best rated first.
#
# The genres left out keep each row to its mood: cartoons and comedies everywhere, horror
# out of the thrillers (it has its own rows), thrillers out of the dramas (checked: five of
# the twenty drama greats were also thriller greats). The dates are tokens, kept current by
# extras/dates.py.
def everyone_watching(media, genres, ratings, imdb=''):
    extra = f'&amp;imdb_ratings={imdb}-10&amp;years={DATE["y3"]}' if media == 'movie' else ''
    return (f'{PLUGIN}info=trakt_mostviewers&amp;tmdb_type={media}&amp;genres={genres}'
            f'&amp;ratings={ratings}-100{extra}&amp;nextpage=false')


def must_watch(media, genres, without, votes, extra=''):
    return (f'{PLUGIN}info=discover&amp;tmdb_type={media}&amp;with_genres={genres}'
            f'&amp;without_genres={without}{extra}&amp;vote_count.gte={votes}'
            f'&amp;sort_by=vote_average.desc&amp;with_id=True&amp;nextpage=false')


def mood(media, genres, since, votes, sort, without='', extra=''):
    date_key = 'primary_release_date' if media == 'movie' else 'first_air_date'
    skip = f'&amp;without_genres={without}' if without else ''
    return (f'{PLUGIN}info=discover&amp;tmdb_type={media}&amp;with_genres={genres}{skip}{extra}'
            f'&amp;{date_key}.gte={since}&amp;vote_count.gte={votes}&amp;sort_by={sort}'
            f'&amp;with_id=True&amp;nextpage=false')


ENGLISH = '&amp;with_original_language=en'
FILM_GENRES = {
    'thrillers': everyone_watching('movie', 'thriller,-animation,-comedy,-horror', 68, '6.5'),
    'horror': everyone_watching('movie', 'horror,-animation,-comedy', 65, '6.0'),
    'dramas': everyone_watching('movie', 'drama,-animation,-comedy,-superhero,-musical,-thriller,-horror', 72, '7.0'),
    'great_thrillers': must_watch('movie', '53', '16,35,27,10751', 6000),
    'great_horror': must_watch('movie', '27', '16,35,10751', 2500),
    'great_dramas': must_watch('movie', '18', '16,35,10751,10749,53', 12000),
    'romance': mood('movie', '10749', DECADE, 40, 'popularity.desc', extra='&amp;with_original_language=hi'),
}
SERIES_GENRES = {
    'thrillers': everyone_watching('tv', 'thriller,-anime,-animation,-comedy,-horror', 75),
    'horror': everyone_watching('tv', 'horror,-anime,-animation,-comedy', 75),
    'dramas': everyone_watching('tv', 'drama,-anime,-animation,-comedy,-superhero,-thriller,-horror', 80),
    'great_dramas': must_watch('tv', '18', f'{NOT_SERIALS},16,35,10751,10765', 2500, ENGLISH),
    'crime': mood('tv', '80,18', DECADE, 300, 'vote_average.desc', f'{NOT_SERIALS},16', ENGLISH),
}

PAGES = {
    1140: {
        'file': 'Custom_1140_Movies.xml',
        'title': 'Movies',
        'rows': [
            # Trakt's weekly chart of unique viewers. (trakt_mostwatched, used here before,
            # is your own history by play count - it showed what you had rewatched.)
            ('rank', 'Top 10 Most Watched This Week',
             f'{PLUGIN}info=trakt_mostviewers&amp;tmdb_type=movie&amp;nextpage=false'),
            ('poster', 'In Cinemas Now', IN_CINEMAS),
            ('poster', 'New Releases',
             f'{PLUGIN}info=discover&amp;tmdb_type=movie&amp;sort_by=primary_release_date.desc'
             f'&amp;primary_release_date.gte={NEW_SINCE}&amp;primary_release_date.lte={TODAY}'
             f'&amp;vote_count.gte=10&amp;nextpage=false'),
            ('poster', "Thrillers Everyone's Watching", FILM_GENRES['thrillers']),
            ('poster', "Horror Everyone's Talking About", FILM_GENRES['horror']),
            ('poster', "Dramas Everyone's Hooked On", FILM_GENRES['dramas']),
            ('poster', 'Blockbusters', BLOCKBUSTERS),
            ('rank', 'Top 10 Hindi Movies Right Now', language_chart('hi')),
            ('poster', 'Hindi Films of the Decade', best_of_language('hi', votes=120)),
            ('poster', 'Bollywood Romance', FILM_GENRES['romance']),
            ('poster', 'Must-Watch Thrillers: The All-Time Greats', FILM_GENRES['great_thrillers']),
            ('rank', 'Top 10 Tamil Movies Right Now', language_chart('ta', votes=10)),
            ('poster', 'Tamil Films of the Decade', best_of_language('ta', votes=60)),
            ('poster', 'Must-Watch Horror: Lights On', FILM_GENRES['great_horror']),
            ('poster', 'Must-Watch Dramas: The Classics', FILM_GENRES['great_dramas']),
            ('poster', 'World Cinema', WORLD_MOVIES),
            ('poster', 'Coming Soon', f'{PLUGIN}info=trakt_anticipated&amp;tmdb_type=movie&amp;nextpage=false'),
        ],
    },
    1141: {
        'file': 'Custom_1141_TVShows.xml',
        'title': 'TV Shows',
        # One numbered chart per network. A show has one originating network, so
        # with_networks partitions them: checked across all six plus the Hindi row and
        # no title appeared in two charts. Held to recent titles with real vote counts,
        # because raw popularity returns whatever airs every weekday.
        'rows': [
            ('rank', 'Top 10 on Netflix', network(213)),
            ('rank', 'Top 10 on Prime Video', network(1024)),
            ('rank', 'Top 10 on HBO', network(49)),
            ('poster', "Thrillers Everyone's Watching", SERIES_GENRES['thrillers']),
            ('rank', 'Top 10 on Apple TV+', network(2552)),
            ('poster', "Horror Everyone's Talking About", SERIES_GENRES['horror']),
            ('rank', 'Top 10 on Hulu', network(453)),
            ('poster', "Dramas Everyone's Hooked On", SERIES_GENRES['dramas']),
            ('rank', 'Top 10 on the BBC', network(4)),
            ('poster', 'Gripping Crime Dramas', SERIES_GENRES['crime']),
            ('poster', 'Must-Watch Drama Series', SERIES_GENRES['great_dramas']),
            ('rank', 'Top 10 Hindi Series Right Now', language_chart('hi', media='tv', votes=10)),
            ('rank', 'Top 10 Tamil Series Right Now', language_chart('ta', media='tv', votes=3, recent=False)),
            ('poster', 'World Series', WORLD_SHOWS),
            ('poster', 'Coming Soon', f'{PLUGIN}info=trakt_anticipated&amp;tmdb_type=tv&amp;nextpage=false'),
        ],
    },
    1142: {
        'file': 'Custom_1142_MyList.xml',
        'title': 'My List',
        # Your Trakt watchlist - what the My List buttons add to - newest first. Upcoming
        # titles stay: adding something before it is out is the point of a list.
        'rows': [
            ('poster', 'Movies', f'{PLUGIN}info=trakt_watchlist&amp;tmdb_type=movie&amp;sort_by=added&amp;sort_how=desc&amp;nextpage=false'),
            ('poster', 'TV Shows', f'{PLUGIN}info=trakt_watchlist&amp;tmdb_type=tv&amp;sort_by=added&amp;sort_how=desc&amp;nextpage=false'),
        ],
    },
}


# Rows are for things you can watch now. TMDb Helper marks a title that is not out yet
# with red italic markup in its label, and lists like these otherwise mix a handful in;
# hide_unaired drops them. Rows that exist to show what is coming keep them.
KEEPS_UNAIRED = ('trakt_anticipated', 'airing_today', 'trakt_ondeck', 'trakt_watchlist')


def watchable(path):
    if any(f'info={name}' in path for name in KEEPS_UNAIRED) or 'hide_unaired' in path:
        return path
    return path.replace('nextpage=false', 'hide_unaired=true&amp;nextpage=false')


def row_id(index):
    return 51 + index


def focus_condition(index, kind):
    """A numbered row's tiles are children, so it needs ControlGroup()."""
    rid = row_id(index)
    return f'ControlGroup({rid}).HasFocus(0)' if kind == 'rank' else f'Control.HasFocus({rid})'


# Rows load as you reach them - see tools/gen_home.py. The first three always load; after
# that a row exists only while the focus is within two rows above it.
EAGER = 3
AHEAD = 2


def lazy(index, rows, xml):
    if index < EAGER:
        return xml
    near = ' | '.join(focus_condition(j, rows[j][0]) for j in range(max(0, index - AHEAD), len(rows)))
    return ('            <control type="group">\n'
            f'                <visible>{near}</visible>\n'
            + '\n'.join('    ' + line for line in xml.split('\n')) + '\n            </control>')


TABS = {1140: 9002, 1141: 9003, 1142: 9006}   # each page's own tab in the tab bar


def build_rows(rows, tab=9000):
    out = []
    for i, (kind, label, content) in enumerate(rows):
        content = watchable(content)
        top = FIRST_ROW_TOP + i * ROW_STRIDE
        onup = 9000 if i == 0 else row_id(i - 1)
        ondown = row_id(i + 1) if i < len(rows) - 1 else 'noop'
        # Back climbs, as on Apple TV: from a row to the top of the page, from there to the
        # tab bar (which shows only while it has focus)
        # (a numbered row cannot take focus itself; its first tile, 7<row>01, can)
        # A control id, not SetFocus(): Kodi treats an id as a move and stops there, but after
        # a command it still runs the window's own Back, which left the page for Home.
        first = '7001' if rows[0][0] == 'rank' else row_id(0)
        onback = f'{tab}' if i == 0 else f'{first}'
        if kind == 'rank':
            row = (f'''            <include content="ATV_RankRow">
                <param name="id" value="{row_id(i)}" />
                <param name="idbase" value="7{i}" />
                <param name="data" value="{6100 + i}" />
                <param name="top" value="{top}" />
                <param name="label" value="{label}" />
                <param name="onup" value="{onup}" />
                <param name="ondown" value="{ondown}" />
                <param name="onback" value="{onback}" />
                <param name="content" value="{content}" />
            </include>''')
        else:
            row = (f'''            <include content="ATV_PosterRow">
                <param name="id" value="{row_id(i)}" />
                <param name="top" value="{top}" />
                <param name="label" value="{label}" />
                <param name="onup" value="{onup}" />
                <param name="ondown" value="{ondown}" />
                <param name="onback" value="{onback}" />
                <param name="content" value="{content}" />
            </include>''')
        out.append(lazy(i, rows, row))
    return '\n'.join(out)


def build_scroll(rows):
    """Steps that add up, so moving one row toggles exactly one animation (see Home.xml)."""
    tops = [FIRST_ROW_TOP + i * ROW_STRIDE for i in range(len(rows))]
    # Offsets are negative (the page moves up). The clamp stops the page once the last
    # row sits at the bottom, so it never scrolls into empty space.
    floor = -(tops[-1] + ROW_HEIGHT - SCREEN_BOTTOM)
    # The first row rests where it is drawn, so the page title above it stays clear;
    # scrolling only starts from the second row.
    offsets = [0 if not i else max(-(top - HEADER_TOP), floor) for i, top in enumerate(tops)]

    lines, previous = [], 0
    for i, offset in enumerate(offsets):
        step = offset - previous
        previous = offset
        if not step:
            continue  # last rows share a position: the page stops there
        at_or_below = ' | '.join(focus_condition(j, rows[j][0]) for j in range(i, len(rows)))
        lines.append(f'            <animation effect="slide" end="0,{step}" time="380" tween="sine" '
                     f'easing="inout" condition="{at_or_below}">Conditional</animation>')
    return '\n'.join(lines), offsets


def backdrop_variable(window_id, rows):
    """The backdrop of whatever is focused in the first row - the page's billboard.

    Only the first row: below it the backdrop has gone, and naming a backdrop for every
    row would have Kodi load a full-size image for each poster passed, unseen. A numbered
    row's tiles are fixed buttons bound to a hidden list, so ListItem means nothing there:
    each tile names its own item. Otherwise - the tab bar, a lower row, the moment the
    page opens - it holds the first title of the first row.
    """
    kind = rows[0][0]
    if kind == 'rank':
        values = [f'\t\t<value condition="Control.HasFocus(70{n}1)">'
                  f'$INFO[Container(6100).ListItemAbsolute({n}).Art(fanart)]</value>' for n in range(10)]
        first = '$INFO[Container(6100).ListItemAbsolute(0).Art(fanart)]'
    else:
        values = [f'\t\t<value condition="Control.HasFocus({row_id(0)})">'
                  f'$INFO[Container({row_id(0)}).ListItem.Art(fanart)]</value>']
        first = f'$INFO[Container({row_id(0)}).ListItemAbsolute(0).Art(fanart)]'
    values.append(f'\t\t<value>{first}</value>')
    return f'\t<variable name="ATV_BrowseFanart{window_id}">\n' + '\n'.join(values) + '\n\t</variable>\n'


def build_page(window_id, spec):
    rows = spec['rows']
    scroll, offsets = build_scroll(rows)
    # The title only gets out of the way once you scroll past the first row, so it is still
    # there when the page opens. The tab bar shows only while it has focus.
    scrolled = ' | '.join(focus_condition(i, kind) for i, (kind, _, _) in enumerate(rows) if i)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- GENERATED by tools/gen_browse.py - edit the generator, not this file.
     {spec['title']}: the shared tab bar, a page title and rows. Numbered rows come from
     tools/gen_rank.py. The page stops scrolling once the last row is at the bottom. -->
<window id="{window_id}">
    <defaultcontrol>{row_id(0)}</defaultcontrol>
    <controls>

        <control type="image">
            <left>0</left><top>0</top><width>1920</width><height>1080</height>
            <texture colordiffuse="FF0B0B0D">white.png</texture>
        </control>

        <!-- The top of the page is backed by the backdrop of whatever has focus in the first
             row, cross-fading as you move along it - this page's billboard. Once you move
             down it scrolls up and away, as Home's does, and the rows below sit on a plain
             dark page: behind every row it competed with the posters and hid the glass and
             focus effects. -->
        <control type="group">
            <animation effect="fade" start="100" end="0" time="380" tween="sine" easing="inout" condition="{scrolled}">Conditional</animation>
            <animation effect="slide" end="0,-320" time="380" tween="sine" easing="inout" condition="{scrolled}">Conditional</animation>
            <control type="image">
                <left>0</left><top>0</top><width>1920</width><height>1080</height>
                <aspectratio align="center" aligny="top">scale</aspectratio>
                <fadetime>500</fadetime>
                <texture background="true">$VAR[ATV_BrowseFanart{window_id}]</texture>
            </control>
            <control type="image">
                <left>0</left><top>0</top><width>1920</width><height>1080</height>
                <texture colordiffuse="8C000000">white.png</texture>
            </control>
            <control type="image">
                <left>0</left><top>0</top><width>1400</width><height>1080</height>
                <texture>atv/grad_left.png</texture>
            </control>
            <control type="image">
                <left>0</left><top>240</top><width>1920</width><height>840</height>
                <texture colordiffuse="FF0B0B0D">atv/grad_bottom.png</texture>
            </control>
        </control>

        <!-- Page title: fades away as soon as you move into the rows -->
        <control type="label">
            <left>90</left><top>142</top><width>900</width><height>70</height>
            <label>{spec['title']}</label>
            <font>atv_pagetitle</font><textcolor>FFFFFFFF</textcolor>
            <animation effect="fade" start="100" end="0" time="300" tween="sine" easing="inout" condition="{scrolled}">Conditional</animation>
        </control>

        <control type="group">
{scroll}

{build_rows(rows, TABS.get(window_id, 9000))}
        </control>

        <!-- Rows above the focused one dissolve into the top edge -->
        <control type="image">
            <left>0</left><top>0</top><width>1920</width><height>190</height>
            <texture>atv/grad_top.png</texture>
            <visible>{scrolled}</visible>
            <animation effect="fade" time="300">VisibleChange</animation>
        </control>

        <include content="ATV_TabBar">
            <param name="hidewhen" value="$EXP[ATV_TabBarHidden]" />
            <param name="ondown" value="{row_id(0)}" />
        </include>

    </controls>
</window>
'''


def main():
    variables = ''.join(backdrop_variable(window_id, spec['rows']) for window_id, spec in PAGES.items())
    with open(os.path.join(ROOT, 'xml', 'Includes_ATV_Browse.xml'), 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!-- GENERATED by tools/gen_browse.py - the Movies and TV pages\' backdrops -->\n'
                '<includes>\n' + variables + '</includes>\n')
    for window_id, spec in PAGES.items():
        path = os.path.join(ROOT, 'xml', spec['file'])
        with open(path, 'w') as f:
            f.write(build_page(window_id, spec))
        print(f"wrote {spec['file']} ({len(spec['rows'])} rows)")


if __name__ == '__main__':
    main()
