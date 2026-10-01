"""Generate xml/Includes_ATV_Rank.xml - the numbered "Top 10" row.

Run from the skin folder:  python3 tools/gen_rank.py

Kodi gives a row's layout no way to know an item's position, and TMDb Helper doesn't tag
items with a rank, so a normal container cannot print "1, 2, 3...". Instead the row is ten
fixed tiles inside a horizontal grouplist (which still scrolls with focus), each bound to
one absolute position of a hidden data list via Container(x).ListItemAbsolute(n) - or, in
ATV_ChartRow, to the skin strings extras/charts.py writes (param chart: in_movie, hi_tv...).

Usage from a window:

    <include content="ATV_RankRow">
        <param name="id" value="51" />            <!-- the grouplist (focus target) -->
        <param name="idbase" value="61" />        <!-- tiles get ids 610..619, buttons 6101..6191 -->
        <param name="data" value="6051" />        <!-- hidden list holding the items -->
        <param name="top" value="1240" />
        <param name="label" value="Top 10 Movies Today" />
        <param name="content" value="plugin://..." />
        <param name="onup" value="50" />
        <param name="ondown" value="52" />
    </include>
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNT = 10
POSTER_W, POSTER_H = 250, 375
SLOT = POSTER_W + 28        # pitch of one tile
POSTER_TOP = 40


def tile(index, art, onclick, visible=''):
    """One numbered tile: the poster, with its rank on it.

    The number sits on the poster, in a dark glass badge in its top-left corner. It was an
    outlined numeral beside the poster, Netflix style, which read as a second, emptier column;
    a big numeral on the poster's foot covered the title most posters print there.
    """
    nav = ''
    if index:
        nav += f'<onleft>$PARAM[idbase]{index - 1}1</onleft>'
    if index < COUNT - 1:
        nav += f'<onright>$PARAM[idbase]{index + 1}1</onright>'
    nav += '<onup>$PARAM[onup]</onup><ondown>$PARAM[ondown]</ondown>'
    focused = f'Control.HasFocus($PARAM[idbase]{index}1)'
    show = f'\n\t\t\t\t\t\t<visible>{visible}</visible>' if visible else ''
    return f"""
					<control type="group" id="$PARAM[idbase]{index}">
						<width>{SLOT}</width><height>{POSTER_TOP + POSTER_H + 40}</height>{show}
						<control type="group">
							<animation effect="zoom" start="100" end="110" center="{POSTER_W // 2},{POSTER_TOP + POSTER_H // 2}" time="220" tween="cubic" easing="out" condition="{focused}">Conditional</animation>
							<control type="image">
								<left>-24</left><top>{POSTER_TOP - 24}</top><width>{POSTER_W + 48}</width><height>{POSTER_H + 48}</height>
								<texture border="64">atv/shadow.png</texture>
								<visible>{focused}</visible>
							</control>
							<control type="image">
								<left>0</left><top>{POSTER_TOP}</top><width>{POSTER_W}</width><height>{POSTER_H}</height>
								<texture colordiffuse="FF1C1C1E" diffuse="atv/mask_poster.png">white.png</texture>
							</control>
							<control type="image">
								<left>0</left><top>{POSTER_TOP}</top><width>{POSTER_W}</width><height>{POSTER_H}</height>
								<aspectratio scalediffuse="false">scale</aspectratio>
								<fadetime>200</fadetime>
								<texture background="true" diffuse="atv/mask_poster.png">{art}</texture>
							</control>
							<!-- the rank: a dark glass badge in the corner, where a poster rarely puts its title -->
							<control type="image">
								<left>12</left><top>{POSTER_TOP + 12}</top><width>72</width><height>72</height>
								<texture border="12" colordiffuse="D90B0B0D">atv/rounded12.png</texture>
							</control>
							<control type="image">
								<left>12</left><top>{POSTER_TOP + 12}</top><width>72</width><height>72</height>
								<texture border="12" colordiffuse="40FFFFFF">atv/ring16.png</texture>
							</control>
							<control type="label">
								<left>12</left><top>{POSTER_TOP + 12}</top><width>72</width><height>72</height>
								<!-- $NUMBER[] because Kodi reads a bare number as a translated-string id -->
								<label>$NUMBER[{index + 1}]</label>
								<font>atv_rank_on</font><textcolor>FFFFFFFF</textcolor>
								<align>center</align><aligny>center</aligny>
							</control>
							<!-- The same light edge as ATV_PosterRow -->
							<control type="image">
								<left>0</left><top>{POSTER_TOP}</top><width>{POSTER_W}</width><height>{POSTER_H}</height>
								<texture border="16" colordiffuse="33FFFFFF">atv/ring16.png</texture>
								<visible>{focused}</visible>
								<animation effect="fade" start="0" end="100" time="220">Visible</animation>
							</control>
						</control>
						<control type="button" id="$PARAM[idbase]{index}1">
							<left>0</left><top>{POSTER_TOP}</top><width>{POSTER_W}</width><height>{POSTER_H}</height>
							<label></label><font></font>
							<texturefocus />
							<texturenofocus />
							<pulseonselect>false</pulseonselect>
							<onclick>{onclick}</onclick>
							<!-- Back belongs on the tile: focus is on it, not on the row around it -->
							<onback>$PARAM[onback]</onback>
							{nav}
						</control>
					</control>"""


def placeholders(condition):
    boxes = ''.join(f"""
					<control type="image">
						<left>{90 + i * SLOT}</left><top>{POSTER_TOP + 40}</top><width>{POSTER_W}</width><height>{POSTER_H}</height>
						<texture colordiffuse="14FFFFFF" diffuse="atv/mask_poster.png">white.png</texture>
					</control>""" for i in range(7))
    return f"""
				<!-- Placeholders while the row loads, so it never sits empty -->
				<control type="group">
					<visible>{condition}</visible>
					<animation effect="fade" start="100" end="45" time="900" pulse="true" condition="true">Conditional</animation>
					<animation effect="fade" time="250">VisibleChange</animation>{boxes}
				</control>"""


def row(name, params, tiles, extra=''):
    params_xml = ''.join(f'\n\t\t<param name="{p}"{"" if v is None else ">" + v + "</param"}{"/" if v is None else ""}>' for p, v in params)
    return f"""
	<include name="{name}">{params_xml}
		<definition>
			<control type="group">
				<top>$PARAM[top]</top>
				<control type="label">
					<left>90</left><top>0</top><width>1400</width><height>44</height>
					<label>$PARAM[label]</label>
					<font>atv_row</font>
					<textcolor>FFFFFFFF</textcolor>
				</control>{extra}
				<control type="grouplist" id="$PARAM[id]">
					<left>90</left><top>40</top><width>1830</width><height>{POSTER_TOP + POSTER_H + 40}</height>
					<orientation>horizontal</orientation>
					<itemgap>0</itemgap>
					<scrolltime tween="sine" easing="inout">380</scrolltime>
					<onup>$PARAM[onup]</onup>
					<ondown>$PARAM[ondown]</ondown>
					<onback>$PARAM[onback]</onback>{tiles}
				</control>
			</control>
		</definition>
	</include>"""


def main():
    # A list's items, read by position from a hidden data list (the Netflix / Prime charts)
    data_tiles = ''.join(tile(i, f'$INFO[Container($PARAM[data]).ListItemAbsolute({i}).Art(poster)]',
                              f'RunScript(special://skin/extras/details.py,open,$PARAM[data],{i})') for i in range(COUNT))
    data_extra = placeholders('Integer.IsEqual(Container($PARAM[data]).NumItems,0)') + f"""
				<!-- Hidden list: holds the ten items the tiles read by position -->
				<control type="list" id="$PARAM[data]">
					<!-- never keep focus: if Kodi drops it here, hand it to the first tile -->
					<onfocus>SetFocus($PARAM[idbase]01)</onfocus>
					<left>0</left><top>1078</top><width>10</width><height>2</height>
					<itemlayout width="1" height="1" />
					<focusedlayout width="1" height="1" />
					<content limit="{COUNT}">$PARAM[content]</content>
				</control>"""
    rank = row('ATV_RankRow', [('id', None), ('idbase', None), ('data', None), ('top', None), ('label', None),
                               ('content', None), ('onup', None), ('ondown', 'noop'), ('onback', 'SetFocus(8001)')],
               data_tiles, data_extra)
    # A chart from what people watch (extras/charts.py), read from skin strings: there at once
    def field(i, name):
        return f'$INFO[Skin.String(ATVTop.$PARAM[chart].{i + 1}.{name})]'
    chart_tiles = ''.join(tile(i, field(i, 'poster'),
                               f'RunScript(special://skin/extras/details.py,title,{field(i, "type")},{field(i, "tmdb")})',
                               f'!String.IsEmpty(Skin.String(ATVTop.$PARAM[chart].{i + 1}.tmdb))') for i in range(COUNT))
    chart = row('ATV_ChartRow', [('id', None), ('idbase', None), ('chart', None), ('top', None), ('label', None),
                                 ('onup', None), ('ondown', 'noop'), ('onback', 'SetFocus(8001)')],
                chart_tiles, placeholders('String.IsEmpty(Skin.String(ATVTop.$PARAM[chart].1.tmdb))'))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<!-- GENERATED by tools/gen_rank.py - edit the generator, not this file -->\n'
           '<includes>' + rank + chart + '\n</includes>\n')
    with open(os.path.join(ROOT, 'xml', 'Includes_ATV_Rank.xml'), 'w') as f:
        f.write(xml)
    print(f'wrote Includes_ATV_Rank.xml (ATV_RankRow, ATV_ChartRow; {COUNT} tiles each)')


if __name__ == '__main__':
    main()
