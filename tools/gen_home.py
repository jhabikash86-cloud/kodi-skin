"""Generate xml/Home.xml from tools/home_template.xml.

Run from the skin folder:  python3 tools/gen_home.py

The hero and the page chrome live in the template. Everything below the hero - the row
line-up, each row's navigation, and the step animations that scroll the page - is worked
out from ROWS here, so adding a row is one line instead of re-deriving four animations
and a stop position by hand.

Row kinds:
    upnext  the wide episode tiles ("Continue Watching"); must be first if present
    rank    a numbered Top 10 (tools/gen_rank.py)
    poster  an ordinary poster row
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = 'plugin://plugin.video.themoviedb.helper/?'

FIRST_ROW_TOP = 860     # the Up Next row sits under the hero
SECOND_ROW_TOP = 1265   # a shorter gap than the rest: the hero's buttons end above it
ROW_STRIDE = 475
ROW_HEIGHT = 455
SCREEN_BOTTOM = 980     # where the last row's bottom comes to rest
HEADER_TOP = 150        # where the focused row's title settles

# Sorting by raw popularity fills these with whatever airs every weekday - Sesame Street,
# Top of the Pops - so the network rows are held to recent titles with real vote counts,
# and the "best of" rows are sorted by rating instead.
# Date windows are filled in by Kodi from extras/dates.py, so rows never go stale.
DATE = {n: f'$INFO[Window(home).Property(ATVDate.{n})]' for n in ('today', 'd45', 'd90', 'd365', 'd540', 'd1095', 'd3650')}
RECENT = DATE['d540']

# Genre ids for the formats that dominate popularity in some countries but are not what
# anyone means by a chart: soap, news, talk, reality, kids.
NOT_SERIALS = '10766,10763,10767,10764,10762'

# TMDb has no "language is not English" filter, so world cinema is done by origin country.
WORLD_CINEMA = (f'{PLUGIN}info=discover&tmdb_type=movie&with_origin_country=KR%7CJP%7CFR%7CES%7CIT'
                f'&sort_by=popularity.desc&primary_release_date.gte={RECENT}'
                f'&vote_count.gte=30&nextpage=false')
THREE_YEARS = DATE['d1095']

# India is the watch region: Netflix, Prime and JioHotstar catalogues differ by country,
# and these are the services that carry content here. HBO, Hulu and the BBC have no
# Indian movie catalogue, so their charts live on the TV page where they are networks.
WATCH_REGION = 'IN'
PROVIDERS = {'Netflix': 8, 'Prime Video': 119, 'JioHotstar': 2336}


def provider_chart(provider_id, votes=20):
    return (f'{PLUGIN}info=discover&tmdb_type=movie&with_watch_providers={provider_id}'
            f'&watch_region={WATCH_REGION}&sort_by=popularity.desc'
            f'&primary_release_date.gte={RECENT}&vote_count.gte={votes}&nextpage=false')


def language_row(code, media='movie', votes=15):
    date_key = 'primary_release_date' if media == 'movie' else 'first_air_date'
    extra = '' if media == 'movie' else f'&without_genres={NOT_SERIALS}&with_id=True'
    return (f'{PLUGIN}info=discover&tmdb_type={media}&with_original_language={code}'
            f'&sort_by=popularity.desc&{date_key}.gte={RECENT}{extra}'
            f'&vote_count.gte={votes}&nextpage=false')


# The hero shows what is in cinemas. TMDb's now_playing carried re-releases (Avengers:
# Endgame, 2019), so it is films that opened in the last six weeks, as on the Movies page.
CINEMA_SINCE = DATE['d45']
HERO = (f'{PLUGIN}info=discover&tmdb_type=movie&primary_release_date.gte={CINEMA_SINCE}'
        f'&primary_release_date.lte={DATE["today"]}&sort_by=popularity.desc'
        f'&vote_count.gte=20&hide_unaired=true&nextpage=false')

# What you paused, from Trakt's on-deck lists, newest first, the last 90 days. Anything under 4% watched is
# left out (TMDb Helper zeroes the progress below that), which drops false starts. Episodes
# and films are separate rows: merged into one row - two <content> lists - they froze Kodi.
def paused(kind):
    # Paused in the last 90 days: older pauses are things you gave up on, and they piled up.
    # (60 dropped every paused episode here - the most recent was 80 days old.) The reload
    # value changes when extras/forget.py removes a tile, so the row fetches again.
    return (f'{PLUGIN}info=trakt_ondeck&tmdb_type={kind}&exclude_key=ResumeTime&exclude_value=0'
            f'&exclude_operator=eq&filter_key=lastplayed.original&filter_value=$DAYS[-90]'
            f'&filter_operator=gt&reload=$INFO[Window(home).Property(ATVContinueReload)]&nextpage=false')


ROWS = [
    ('upnext', 'Continue Watching', paused('tv')),
    ('upnext', 'Continue Watching Films', paused('movie')),
    ('rank', 'Top 10 Movies Right Now',
     f'{PLUGIN}info=trakt_trending&tmdb_type=movie&nextpage=false'),
    ('rank', 'Top 10 Shows Right Now',
     f'{PLUGIN}info=trakt_trending&tmdb_type=tv&nextpage=false'),
    ('poster', 'Recommended for You',
     f'{PLUGIN}info=trakt_recommendations&tmdb_type=movie&nextpage=false'),
    # Follows the last film you finished - the row's own label names it. The path is a
    # variable that stays empty until that film is known (see Includes_ATV.xml).
    ('poster', 'Because You Watched $INFO[Container(6070).ListItem.Title]',
     '$VAR[ATV_BecauseYouWatchedPath]'),
    ('rank', 'Top 10 on Netflix', provider_chart(PROVIDERS['Netflix'])),
    ('rank', 'Top 10 on Prime Video', provider_chart(PROVIDERS['Prime Video'])),
    ('rank', 'Top 10 on JioHotstar', provider_chart(PROVIDERS['JioHotstar'])),
    ('poster', 'Trending in Hindi', language_row('hi')),
    ('poster', 'Trending in Tamil', language_row('ta', votes=10)),
    ('poster', 'World Cinema', WORLD_CINEMA),
]

RANK_IDBASE = {}  # filled in below: one distinct tile-id base per numbered row


def row_id(index):
    return 50 + index


def tops():
    out = [FIRST_ROW_TOP, SECOND_ROW_TOP]
    while len(out) < len(ROWS):
        out.append(out[-1] + ROW_STRIDE)
    return out[:len(ROWS)]


def focus_condition(index):
    """A numbered row's tiles are its children, so it needs ControlGroup()."""
    rid = row_id(index)
    return f'ControlGroup({rid}).HasFocus(0)' if ROWS[index][0] == 'rank' else f'Control.HasFocus({rid})'


def build_scroll():
    t = tops()
    floor = -(t[-1] + ROW_HEIGHT - SCREEN_BOTTOM)
    offsets = [max(-(top - HEADER_TOP), floor) for top in t]

    lines = ['            <!-- Page scroll, built from steps that add up rather than one absolute position',
             '                 per row. Moving one row toggles exactly ONE of these, so nothing overlaps:',
             '                 with absolute positions Kodi runs the old row\'s slide backwards while the new',
             '                 one plays forward and adds them, which overshot badly with ease-out and',
             '                 hesitated with a slow-start curve. The last rows share an offset, so the page',
             '                 stops with the final row at the bottom.',
             '                 Totals: ' + ', '.join(f'{row_id(i)} {o}' for i, o in enumerate(offsets)) + ' -->']
    previous = 0
    for i, offset in enumerate(offsets):
        step = offset - previous
        previous = offset
        if not step:
            continue
        at_or_below = ' | '.join(focus_condition(j) for j in range(i, len(ROWS)))
        guard = ''
        if i == 1 and ROWS[0][0] == 'upnext':
            # With no Continue Watching row the rows below have already moved up into its
            # place, so this step would double up.
            guard = '!$EXP[ATV_UpNextEmpty] + '
        condition = f'{guard}[{at_or_below}]' if guard else at_or_below
        lines.append(f'            <animation effect="slide" end="0,{step}" time="380" tween="sine" '
                     f'easing="inout" condition="{condition}">Conditional</animation>')
    return '\n'.join(lines)


# Rows are for things you can watch now. TMDb Helper marks a title that is not out yet
# with red italic markup in its label, and lists like these otherwise mix a handful in;
# hide_unaired drops them. Rows that exist to show what is coming keep them.
KEEPS_UNAIRED = ('trakt_anticipated', 'airing_today', 'trakt_ondeck')


def watchable(path):
    if any(f'info={name}' in path for name in KEEPS_UNAIRED) or 'hide_unaired' in path:
        return path
    return path.replace('nextpage=false', 'hide_unaired=true&nextpage=false')


def build_row(index, top):
    kind, label, content = ROWS[index]
    content = watchable(content).replace('&', '&amp;')
    onup = 8001 if index == 0 else row_id(index - 1)
    ondown = f'\n                    <param name="ondown" value="{row_id(index + 1)}" />' if index < len(ROWS) - 1 else ''
    if kind == 'upnext':
        # the first row's emptiness collapses the page (ATV_UpNextEmpty); a later one only hides its title
        empty = '' if index == 0 else f'\n                <param name="empty" value="Integer.IsEqual(Container({row_id(index)}).NumItems,0)" />'
        return f'''            <include content="ATV_UpNextRow">
                <param name="id" value="{row_id(index)}" />
                <param name="top" value="{top}" />
                <param name="label" value="{label}" />
                <param name="onup" value="{onup}" />{ondown.replace(chr(10) + " " * 20, chr(10) + " " * 16)}
                <param name="content" value="{content}" />{empty}
            </include>'''
    if kind == 'rank':
        return f'''                <include content="ATV_RankRow">
                    <param name="id" value="{row_id(index)}" />
                    <param name="idbase" value="{RANK_IDBASE[index]}" />
                    <param name="data" value="{6050 + index}" />
                    <param name="top" value="{top}" />
                    <param name="label" value="{label}" />
                    <param name="onup" value="{onup}" />{ondown}
                    <param name="content" value="{content}" />
                </include>'''
    return f'''                <include content="ATV_PosterRow">
                    <param name="id" value="{row_id(index)}" />
                    <param name="top" value="{top}" />
                    <param name="label" value="{label}" />
                    <param name="onup" value="{onup}" />{ondown}
                    <param name="content" value="{content}" />
                </include>'''


# Rows load as you reach them. A row Kodi is not drawing asks for nothing, so every row from
# the fourth down exists only while the focus is within two rows above it: opening Home
# asked TMDb Helper for all twelve rows at once, a dozen Python jobs competing for the
# Xbox's CPU while the two rows on screen waited their turn. The first three always load.
EAGER = 3
AHEAD = 2


def lazy(index, xml):
    if index < EAGER:
        return xml
    near = ' | '.join(focus_condition(j) for j in range(max(0, index - AHEAD), len(ROWS)))
    indent = ' ' * (len(xml) - len(xml.lstrip(' ')))
    return (f'{indent}<control type="group">\n{indent}    <visible>{near}</visible>\n'
            + '\n'.join('    ' + line for line in xml.split('\n')) + f'\n{indent}</control>')


def build_rows():
    t = tops()
    has_upnext = ROWS[0][0] == 'upnext'
    out = ['            <!-- ===== ROWS ===== -->']
    start = 0
    if has_upnext:
        out.append('''            <!-- Continue Watching: the films and episodes you actually paused (Trakt on deck),
                 the more recently used list first. trakt_nextepisodes looks tidier (one row per
                 show) but only lists shows you have FINISHED an episode of, which dropped most
                 of the row. -->''')
        out.append(build_row(0, t[0]))
        out.append('')
        shift = t[1] - t[0]
        out.append('            <control type="group">')
        out.append(f'                <animation effect="slide" end="0,-{shift}" time="400" tween="quadratic" '
                   f'easing="inout" condition="$EXP[ATV_UpNextEmpty]">Conditional</animation>')
        start = 1
    for i in range(start, len(ROWS)):
        out.append(lazy(i, build_row(i, t[i])))
    if has_upnext:
        out.append('            </control>')
    return '\n'.join(out)


def build_expression():
    """ATV_RowsFocused has to name every row, so it is written from the same list."""
    return ' | '.join(focus_condition(i) for i in range(len(ROWS)))


def main():
    base = 61
    for i, (kind, _, _) in enumerate(ROWS):
        if kind == 'rank':
            RANK_IDBASE[i] = base
            base += 1

    with open(os.path.join(ROOT, 'tools', 'home_template.xml')) as f:
        template = f.read()
    xml = (template.replace('{SCROLL}', build_scroll()).replace('{ROWS}', build_rows())
           .replace('{HERO}', HERO.replace('&', '&amp;')))
    with open(os.path.join(ROOT, 'xml', 'Home.xml'), 'w') as f:
        f.write(xml)

    # Keep the shared expression in step with the row list.
    p = os.path.join(ROOT, 'xml', 'Includes_ATV.xml')
    with open(p) as f:
        inc = f.read()
    start = inc.index('<expression name="ATV_RowsFocused">')
    end = inc.index('</expression>', start)
    inc = inc[:start] + f'<expression name="ATV_RowsFocused">{build_expression()}' + inc[end:]
    with open(p, 'w') as f:
        f.write(inc)
    print(f'wrote Home.xml ({len(ROWS)} rows) and refreshed ATV_RowsFocused')


if __name__ == '__main__':
    main()
