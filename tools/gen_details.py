"""Generate the title pages (xml/Custom_1130..1134) and their per-page variables.

Run from the skin folder:  python3 tools/gen_details.py

Why five windows: Kodi 21 always closes a custom window on Back (a control's <onback>
runs but can't stop it). Giving each level of "title -> recommended title -> ..." its own
window lets Kodi's normal window history do the Back navigation. extras/details.py picks
the next page and fills Skin.String(DetailTypeN) / Skin.String(DetailIDN).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = 5

TEMPLATE = os.path.join(ROOT, 'tools', 'details_template.xml')

VARIABLES = '''
	<!-- ===== Title page {n} (window 113{n}) ===== -->
	<expression name="ATV_DetailIsTV{n}">String.IsEqual(Skin.String(DetailType{n}),tv)</expression>
	<variable name="ATV_DetailPath{n}">
		<value>plugin://plugin.video.themoviedb.helper/?info=details&amp;tmdb_type=$INFO[Skin.String(DetailType{n})]&amp;tmdb_id=$INFO[Skin.String(DetailID{n})]&amp;nextpage=false</value>
	</variable>
	<!-- The details listing is this title's, not the one this page showed last. Kodi keeps a
	     page's previous listing and shows it until the new one lands, so everything read
	     from Container(9500) waits on this. -->
	<expression name="ATV_DetailReady{n}">String.IsEqual(Container(9500).ListItem.UniqueID(tmdb),Skin.String(DetailID{n})) + !Container(9500).IsUpdating</expression>
	<!-- Until then the page shows the tile that was clicked: extras/details.py copies its
	     backdrop, logo and title across before opening the page, so it opens on the right
	     picture instead of the last title's. The URLs are the same ones the details bring,
	     so nothing is fetched twice. -->
	<variable name="ATV_DetailFanart{n}">
		<value condition="$EXP[ATV_DetailReady{n}] + !String.IsEmpty(Container(9500).ListItem.Art(fanart))">$INFO[Container(9500).ListItem.Art(fanart)]</value>
		<value>$INFO[Skin.String(DetailFanart{n})]</value>
	</variable>
	<variable name="ATV_DetailLogo{n}">
		<value condition="$EXP[ATV_DetailReady{n}] + !String.IsEmpty(Container(9500).ListItem.Art(clearlogo))">$INFO[Container(9500).ListItem.Art(clearlogo)]</value>
		<value>$INFO[Skin.String(DetailLogo{n})]</value>
	</variable>
	<expression name="ATV_DetailHasLogo{n}">[$EXP[ATV_DetailReady{n}] + !String.IsEmpty(Container(9500).ListItem.Art(clearlogo))] | !String.IsEmpty(Skin.String(DetailLogo{n}))</expression>
	<variable name="ATV_DetailTitle{n}">
		<value condition="$EXP[ATV_DetailReady{n}]">$INFO[Container(9500).ListItem.Title]</value>
		<value>$INFO[Skin.String(DetailTitle{n})]</value>
	</variable>
	<!-- More Like This: same genres, and the same language, so a Tamil film leads to more
	     Tamil cinema. extras/details.py composes the filter from this title's own details
	     once they land - the tile that was clicked can carry only its first genre, and
	     "Comedy" alone turned an R-rated horror comedy into Toy Story and PAW Patrol. Empty
	     until then, so the row fetches once, for the right title. "similar" means the
	     details had no genres to go on. -->
	<variable name="ATV_DetailGenrePath{n}">
		<value condition="String.IsEqual(Skin.String(DetailDiscover{n}),similar)">plugin://plugin.video.themoviedb.helper/?info=similar&amp;tmdb_type=$INFO[Skin.String(DetailType{n})]&amp;tmdb_id=$INFO[Skin.String(DetailID{n})]&amp;hide_unaired=true&amp;nextpage=false</value>
		<value condition="!String.IsEmpty(Skin.String(DetailDiscover{n}))">plugin://plugin.video.themoviedb.helper/?info=discover&amp;tmdb_type=$INFO[Skin.String(DetailType{n})]&amp;$INFO[Skin.String(DetailDiscover{n})]&amp;exclude_key=tmdb_id&amp;exclude_value=$INFO[Skin.String(DetailID{n})]&amp;exclude_operator=eq&amp;hide_unaired=true&amp;nextpage=false</value>
	</variable>
	<!-- Everything below waits for this title's details. TMDb Helper locks a title while it
	     builds its details, and every list about that title - seasons, episodes, cast,
	     recommendations - waits on the same lock and, when it gets it, fetches the details
	     again for itself. Opened all at once they queued up past the lock's 10s limit, and
	     the last in line failed with a TMDb Helper error - a page with no episodes, or no
	     rows at all. Once the details are in, each of these reads them from the cache and
	     holds the lock for a moment. Empty for movies, so the hidden season rows never ask. -->
	<variable name="ATV_SeasonsPath{n}">
		<value condition="$EXP[ATV_DetailIsTV{n}] + $EXP[ATV_DetailReady{n}]">plugin://plugin.video.themoviedb.helper/?info=seasons&amp;tmdb_type=tv&amp;tmdb_id=$INFO[Skin.String(DetailID{n})]&amp;exclude_key=season&amp;exclude_value=-1&amp;exclude_operator=eq&amp;nextpage=false</value>
	</variable>
	<variable name="ATV_EpisodesPath{n}">
		<value condition="$EXP[ATV_DetailIsTV{n}] + $EXP[ATV_DetailReady{n}]">plugin://plugin.video.themoviedb.helper/?info=episodes&amp;tmdb_type=tv&amp;tmdb_id=$INFO[Skin.String(DetailID{n})]&amp;season=$VAR[ATV_DetailSeason]&amp;nextpage=false</value>
	</variable>
	<variable name="ATV_CastPath{n}">
		<value condition="$EXP[ATV_DetailReady{n}]">plugin://plugin.video.themoviedb.helper/?info=cast&amp;tmdb_type=$INFO[Skin.String(DetailType{n})]&amp;tmdb_id=$INFO[Skin.String(DetailID{n})]&amp;nextpage=false</value>
	</variable>
	<variable name="ATV_RecommendedPath{n}">
		<value condition="$EXP[ATV_DetailReady{n}]">plugin://plugin.video.themoviedb.helper/?info=recommendations&amp;tmdb_type=$INFO[Skin.String(DetailType{n})]&amp;tmdb_id=$INFO[Skin.String(DetailID{n})]&amp;hide_unaired=true&amp;nextpage=false</value>
	</variable>
	<!-- A show TMDb has no seasons for yet - announced, not aired -->
	<expression name="ATV_DetailNoSeasons{n}">$EXP[ATV_DetailIsTV{n}] + $EXP[ATV_DetailReady{n}] + Integer.IsEqual(Container(9610).NumItems,0) + !Container(9610).IsUpdating</expression>
	<variable name="ATV_DetailMeta{n}">
		<value condition="$EXP[ATV_DetailIsTV{n}]">TV Show$INFO[Container(9500).ListItem.Year,  ·  ]$INFO[Container(9500).ListItem.Genre,  ·  ]$INFO[Container(9500).ListItem.MPAA,  ·  ]$INFO[Container(9500).ListItem.Rating,  ·  ★ ]</value>
		<value>Movie$INFO[Container(9500).ListItem.Year,  ·  ]$INFO[Container(9500).ListItem.Genre,  ·  ]$INFO[Container(9500).ListItem.Duration(mins),  ·  , min]$INFO[Container(9500).ListItem.MPAA,  ·  ]$INFO[Container(9500).ListItem.Rating,  ·  ★ ]</value>
	</variable>
	<!-- extras/details.py fills DetailNext{n} just after the page opens ("Play S1 E4" or
	     "Resume S1 E3"), so the button names the episode Play will actually start. Until
	     that lands - and for films - it just says Play. -->
	<variable name="ATV_DetailPlayLabel{n}">
		<value condition="!String.IsEmpty(Skin.String(DetailNext{n}))">$INFO[Skin.String(DetailNext{n})]</value>
		<value>Play</value>
	</variable>
'''


def main():
    with open(TEMPLATE) as f:
        template = f.read()
    for n in range(PAGES):
        with open(os.path.join(ROOT, 'xml', f'Custom_113{n}_Details.xml'), 'w') as f:
            f.write(template.replace('§', str(n)))
    with open(os.path.join(ROOT, 'xml', 'Includes_ATV_Details.xml'), 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!-- GENERATED by tools/gen_details.py - per-page variables for the title pages -->\n'
                '<includes>' + ''.join(VARIABLES.format(n=n) for n in range(PAGES)) + '</includes>\n')
    print(f'wrote {PAGES} title pages + Includes_ATV_Details.xml')


if __name__ == '__main__':
    main()
