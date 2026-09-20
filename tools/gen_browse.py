"""Generate the Movies (1140) and TV Shows (1141) pages.

Run from the skin folder:  python3 tools/gen_browse.py

Each page is the shared tab bar, a page title and a list of rows. Rows are either a
normal poster row or a numbered Top 10 row (tools/gen_rank.py). Geometry, the
step-based page scroll and the bottom stop are all worked out from ROWS below, so
adding a row is one line - the rest follows.
"""
import datetime
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = 'plugin://plugin.video.themoviedb.helper/?'

FIRST_ROW_TOP = 260
ROW_STRIDE = 400
ROW_HEIGHT = 380          # a row's content, used for the bottom stop
SCREEN_BOTTOM = 1040      # leave a margin under the last row
HEADER_TOP = 150          # where the focused row's title settles

# Rows should show what is current, not all-time favourites. Trakt's trending and
# most-watched lists are "what people are playing right now"; for the language rows TMDb
# has no such list, so they use popularity limited to recent releases. Re-run this
# generator now and then to move that window forward.
RECENT_SINCE = (datetime.date.today() - datetime.timedelta(days=540)).isoformat()

PAGES = {
    1140: {
        'file': 'Custom_1140_Movies.xml',
        'title': 'Movies',
        'rows': [
            ('rank', 'Top 10 Most Watched This Week',
             f'{PLUGIN}info=trakt_mostwatched&amp;tmdb_type=movie&amp;period=weekly&amp;nextpage=false'),
            ('poster', 'Popular', f'{PLUGIN}info=popular&amp;tmdb_type=movie&amp;nextpage=false'),
            ('poster', 'In Cinemas Now', f'{PLUGIN}info=now_playing&amp;tmdb_type=movie&amp;nextpage=false'),
            ('rank', 'Top 10 Hindi Movies Right Now',
             f'{PLUGIN}info=discover&amp;tmdb_type=movie&amp;with_original_language=hi&amp;sort_by=popularity.desc'
             f'&amp;primary_release_date.gte={RECENT_SINCE}&amp;nextpage=false'),
            ('poster', 'Top Rated', f'{PLUGIN}info=top_rated&amp;tmdb_type=movie&amp;nextpage=false'),
            ('poster', 'Action', f'{PLUGIN}info=discover&amp;tmdb_type=movie&amp;with_genres=28&amp;with_id=True&amp;sort_by=popularity.desc&amp;nextpage=false'),
            ('poster', 'Comedy', f'{PLUGIN}info=discover&amp;tmdb_type=movie&amp;with_genres=35&amp;with_id=True&amp;sort_by=popularity.desc&amp;nextpage=false'),
        ],
    },
    1141: {
        'file': 'Custom_1141_TVShows.xml',
        'title': 'TV Shows',
        'rows': [
            ('rank', 'Top 10 Shows Trending Now', f'{PLUGIN}info=trakt_trending&amp;tmdb_type=tv&amp;nextpage=false'),
            ('poster', 'Popular', f'{PLUGIN}info=popular&amp;tmdb_type=tv&amp;nextpage=false'),
            ('poster', 'Airing Today', f'{PLUGIN}info=airing_today&amp;tmdb_type=tv&amp;nextpage=false'),
            ('rank', 'Top 10 Hindi Shows Right Now',
             f'{PLUGIN}info=discover&amp;tmdb_type=tv&amp;with_original_language=hi&amp;sort_by=popularity.desc'
             f'&amp;first_air_date.gte={RECENT_SINCE}&amp;nextpage=false'),
            ('poster', 'Top Rated', f'{PLUGIN}info=top_rated&amp;tmdb_type=tv&amp;nextpage=false'),
            ('poster', 'Drama', f'{PLUGIN}info=discover&amp;tmdb_type=tv&amp;with_genres=18&amp;with_id=True&amp;sort_by=popularity.desc&amp;nextpage=false'),
            ('poster', 'Crime', f'{PLUGIN}info=discover&amp;tmdb_type=tv&amp;with_genres=80&amp;with_id=True&amp;sort_by=popularity.desc&amp;nextpage=false'),
        ],
    },
}


def row_id(index):
    return 51 + index


def focus_condition(index, kind):
    """A numbered row's tiles are children, so it needs ControlGroup()."""
    rid = row_id(index)
    return f'ControlGroup({rid}).HasFocus(0)' if kind == 'rank' else f'Control.HasFocus({rid})'


def build_rows(rows):
    out = []
    for i, (kind, label, content) in enumerate(rows):
        top = FIRST_ROW_TOP + i * ROW_STRIDE
        onup = 9000 if i == 0 else row_id(i - 1)
        ondown = row_id(i + 1) if i < len(rows) - 1 else 'noop'
        if kind == 'rank':
            out.append(f'''            <include content="ATV_RankRow">
                <param name="id" value="{row_id(i)}" />
                <param name="idbase" value="7{i}" />
                <param name="data" value="{6100 + i}" />
                <param name="top" value="{top}" />
                <param name="label" value="{label}" />
                <param name="onup" value="{onup}" />
                <param name="ondown" value="{ondown}" />
                <param name="onback" value="noop" />
                <param name="content" value="{content}" />
            </include>''')
        else:
            out.append(f'''            <include content="ATV_PosterRow">
                <param name="id" value="{row_id(i)}" />
                <param name="top" value="{top}" />
                <param name="label" value="{label}" />
                <param name="onup" value="{onup}" />
                <param name="ondown" value="{ondown}" />
                <param name="onback" value="noop" />
                <param name="content" value="{content}" />
            </include>''')
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


def build_page(window_id, spec):
    rows = spec['rows']
    scroll, offsets = build_scroll(rows)
    # The title and tab bar only get out of the way once you scroll past the first row,
    # so both are still there when the page opens.
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

        <!-- Page title: fades away as soon as you move into the rows -->
        <control type="label">
            <left>90</left><top>142</top><width>900</width><height>70</height>
            <label>{spec['title']}</label>
            <font>atv_pagetitle</font><textcolor>FFFFFFFF</textcolor>
            <animation effect="fade" start="100" end="0" time="300" tween="sine" easing="inout" condition="{scrolled}">Conditional</animation>
        </control>

        <control type="group">
{scroll}

{build_rows(rows)}
        </control>

        <!-- Rows above the focused one dissolve into the top edge -->
        <control type="image">
            <left>0</left><top>0</top><width>1920</width><height>190</height>
            <texture>atv/grad_top.png</texture>
            <visible>{scrolled}</visible>
            <animation effect="fade" time="300">VisibleChange</animation>
        </control>

        <include content="ATV_TabBar">
            <param name="hidewhen" value="{scrolled}" />
            <param name="ondown" value="{row_id(0)}" />
        </include>

    </controls>
</window>
'''


def main():
    for window_id, spec in PAGES.items():
        path = os.path.join(ROOT, 'xml', spec['file'])
        with open(path, 'w') as f:
            f.write(build_page(window_id, spec))
        print(f"wrote {spec['file']} ({len(spec['rows'])} rows)")


if __name__ == '__main__':
    main()
