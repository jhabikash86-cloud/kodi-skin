"""Generate xml/Custom_1120.xml + Custom_1121.xml: Netflix-style live search, Apple TV styling.

Run from the skin folder:  python3 tools/gen_search.py .
"""
import os
import re
import sys

OUT = sys.argv[1]
SCRIPT = 'special://skin/extras/search.py'
KEYS = list('abcdefghijklmnopqrstuvwxyz1234567890')

key_items = []
for k in KEYS:
    key_items.append(f'''                    <item>
                        <label>{('$NUMBER[' + k + ']') if k.isdigit() else k.upper()}</label>
                        <onclick>Skin.SetString(SearchQuery,$INFO[Skin.String(SearchQuery)]{k})</onclick>
                        <onclick>Skin.SetString(SearchQueryURL,$INFO[Skin.String(SearchQueryURL)]{k})</onclick>
                        <onclick>Skin.Reset(SearchPersonID)</onclick>
                        <onclick>Skin.Reset(SearchPersonName)</onclick>
                    </item>''')
key_items = '\n'.join(key_items)


def key_button(cid, left, width, label, action, nav):
    return f'''            <control type="button" id="{cid}">
                <left>{left}</left><top>0</top><width>{width}</width><height>64</height>
                <label>{label}</label>
                <font>atv_button</font>
                <textcolor>E6FFFFFF</textcolor><focusedcolor>FF0B0B0D</focusedcolor>
                <align>center</align><aligny>center</aligny>
                <texturefocus border="12" colordiffuse="FFFFFFFF">atv/rounded12.png</texturefocus>
                <texturenofocus border="12" colordiffuse="1FFFFFFF">atv/rounded12.png</texturenofocus>
                <pulseonselect>false</pulseonselect>
                <animation effect="zoom" start="100" end="106" center="auto" time="160" tween="cubic" easing="out">Focus</animation>
                <animation effect="zoom" start="106" end="100" center="auto" time="140" tween="cubic" easing="out">Unfocus</animation>
                <onclick>RunScript({SCRIPT},{action})</onclick>
{nav}
            </control>'''


def poster_row(cid, top, header_var, path_var, nav):
    tile = '''<control type="image">
                        <left>20</left><top>24</top><width>170</width><height>255</height>
                        <texture colordiffuse="FF1C1C1E" diffuse="atv/mask_poster.png">white.png</texture>
                    </control>
                    <control type="label">
                        <left>32</left><top>24</top><width>146</width><height>255</height>
                        <label>$INFO[ListItem.Label]</label>
                        <font>atv_small</font><textcolor>B3FFFFFF</textcolor>
                        <align>center</align><aligny>center</aligny><wrapmultiline>true</wrapmultiline>
                        <visible>String.IsEmpty(ListItem.Art(poster))</visible>
                    </control>
                    <control type="image">
                        <left>20</left><top>24</top><width>170</width><height>255</height>
                        <aspectratio scalediffuse="false">scale</aspectratio>
                        <texture background="true" diffuse="atv/mask_poster.png">$INFO[ListItem.Art(poster)]</texture>
                    </control>'''
    return f'''        <!-- {header_var} -->
        <control type="label">
            <left>700</left><top>{top}</top><width>1100</width><height>40</height>
            <label>$VAR[{header_var}]</label>
            <font>atv_row</font><textcolor>FFFFFFFF</textcolor>
        </control>
        <control type="label">
            <left>700</left><top>{top}</top><width>1130</width><height>40</height>
            <label>Searching…</label>
            <font>atv_small</font><textcolor>80FFFFFF</textcolor>
            <align>right</align><aligny>center</aligny>
            <visible>Container({cid}).IsUpdating</visible>
        </control>
        <control type="list" id="{cid}">
            <left>680</left><top>{top + 36}</top><width>1240</width><height>310</height>
            <orientation>horizontal</orientation>
            <scrolltime tween="cubic" easing="out">380</scrolltime>
            <preloaditems>2</preloaditems>
            <onclick>RunScript(special://skin/extras/details.py,open,{cid})</onclick>
{nav}
            <itemlayout width="198" height="310">
                    {tile}
            </itemlayout>
            <focusedlayout width="198" height="310">
                <control type="group">
                    <include content="ATV_Lift"><param name="center" value="105,151" /></include>
                    <control type="image">
                        <left>-20</left><top>-12</top><width>250</width><height>335</height>
                        <texture border="64">atv/shadow.png</texture>
                        <animation effect="fade" start="0" end="100" time="200">Focus</animation>
                        <animation effect="fade" start="100" end="0" time="150">Unfocus</animation>
                    </control>
                    {tile}
                </control>
            </focusedlayout>
            <content target="videos">$VAR[{path_var}]</content>
        </control>'''


xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- ATV Minimal: live search. Type on the left, results update as you go (Netflix style):
     people ("Explore titles related to"), movies and TV shows. Pick a person to see their titles. -->
<window id="{{WINDOW_ID}}">
    <defaultcontrol>{{DEFAULT}}</defaultcontrol>
{{ONLOAD}}
    <controls>

        <!-- ===================== BACKGROUND ===================== -->
        <control type="image">
            <left>0</left><top>0</top><width>1920</width><height>1080</height>
            <texture colordiffuse="FF0B0B0D">white.png</texture>
        </control>
        <control type="image">
            <left>0</left><top>0</top><width>1920</width><height>1080</height>
            <aspectratio align="center" aligny="top">scale</aspectratio>
            <fadetime>500</fadetime>
            <colordiffuse>4DFFFFFF</colordiffuse>
            <texture background="true">$VAR[ATV_SearchFanart]</texture>
            <visible>Control.HasFocus(8120) | Control.HasFocus(8130)</visible>
            <animation effect="fade" time="400">VisibleChange</animation>
        </control>
        <control type="image">
            <left>0</left><top>0</top><width>1100</width><height>1080</height>
            <texture>atv/grad_left.png</texture>
        </control>
        <control type="image">
            <left>0</left><top>540</top><width>1920</width><height>540</height>
            <texture colordiffuse="CC0B0B0D">atv/grad_bottom.png</texture>
        </control>

        <!-- ===================== LEFT: QUERY + KEYBOARD ===================== -->

        <control type="label">
            <left>90</left><top>56</top><width>520</width><height>60</height>
            <label>Search</label>
            <font>atv_title</font><textcolor>FFFFFFFF</textcolor>
        </control>

        <!-- Query field (select it to type with a keyboard / phone remote) -->
        <control type="button" id="8100">
            <left>90</left><top>140</top><width>516</width><height>84</height>
            <label></label>
            <texturefocus border="42" colordiffuse="4DFFFFFF">atv/pill_84.png</texturefocus>
            <texturenofocus border="42" colordiffuse="1FFFFFFF">atv/pill_84.png</texturenofocus>
            <pulseonselect>false</pulseonselect>
            <onclick>RunScript({SCRIPT},keyboard)</onclick>
            <ondown>8201</ondown>
            <onright>8120</onright>
        </control>
        <control type="label">
            <left>126</left><top>140</top><width>450</width><height>84</height>
            <label>Movies, shows, actors</label>
            <font>atv_row</font><textcolor>66FFFFFF</textcolor>
            <aligny>center</aligny>
            <visible>String.IsEmpty(Skin.String(SearchQuery))</visible>
        </control>
        <control type="label">
            <left>126</left><top>140</top><width>450</width><height>84</height>
            <label>$INFO[Skin.String(SearchQuery)]</label>
            <font>atv_row</font><textcolor>FFFFFFFF</textcolor>
            <aligny>center</aligny>
            <scroll>false</scroll>
        </control>
        <!-- Blinking caret: same text in transparent, followed by a bar -->
        <control type="label">
            <left>124</left><top>140</top><width>450</width><height>84</height>
            <label>[COLOR 00FFFFFF]$INFO[Skin.String(SearchQuery)][/COLOR]|</label>
            <font>atv_row</font><textcolor>FFFFFFFF</textcolor>
            <aligny>center</aligny>
            <animation effect="fade" start="100" end="0" time="550" pulse="true" condition="true">Conditional</animation>
        </control>

        <!-- Space / Delete / Clear -->
        <control type="group">
            <left>90</left><top>250</top>
{key_button(8201, 0, 196, "Space", "space", "                <onup>8100</onup><ondown>8200</ondown><onright>8202</onright>")}
{key_button(8202, 204, 160, "Delete", "delete", "                <onup>8100</onup><ondown>8200</ondown><onleft>8201</onleft><onright>8203</onright>")}
{key_button(8203, 372, 144, "Clear", "clear", "                <onup>8100</onup><ondown>8200</ondown><onleft>8202</onleft><onright>8120</onright>")}
        </control>

        <!-- A-Z 0-9 grid: every key updates the results immediately -->
        <control type="panel" id="8200">
            <left>90</left><top>334</top><width>516</width><height>516</height>
            <orientation>vertical</orientation>
            <scrolltime>0</scrolltime>
            <onup>8201</onup>
            <ondown>8204</ondown>
            <onright>8120</onright>
            <itemlayout width="86" height="86">
                <control type="image">
                    <left>0</left><top>0</top><width>78</width><height>78</height>
                    <texture border="12" colordiffuse="14FFFFFF">atv/rounded12.png</texture>
                </control>
                <control type="label">
                    <left>0</left><top>0</top><width>78</width><height>78</height>
                    <label>$INFO[ListItem.Label]</label>
                    <font>atv_key</font><textcolor>E6FFFFFF</textcolor>
                    <align>center</align><aligny>center</aligny>
                </control>
            </itemlayout>
            <focusedlayout width="86" height="86">
                <control type="group">
                    <animation effect="zoom" start="100" end="110" center="39,39" time="140" tween="cubic" easing="out">Focus</animation>
                    <control type="image">
                        <left>0</left><top>0</top><width>78</width><height>78</height>
                        <texture border="12" colordiffuse="FFFFFFFF">atv/rounded12.png</texture>
                        <visible>Control.HasFocus(8200)</visible>
                    </control>
                    <control type="image">
                        <left>0</left><top>0</top><width>78</width><height>78</height>
                        <texture border="12" colordiffuse="14FFFFFF">atv/rounded12.png</texture>
                        <visible>!Control.HasFocus(8200)</visible>
                    </control>
                    <control type="label">
                        <left>0</left><top>0</top><width>78</width><height>78</height>
                        <label>$INFO[ListItem.Label]</label>
                        <font>atv_key</font><textcolor>FF0B0B0D</textcolor>
                        <align>center</align><aligny>center</aligny>
                        <visible>Control.HasFocus(8200)</visible>
                    </control>
                    <control type="label">
                        <left>0</left><top>0</top><width>78</width><height>78</height>
                        <label>$INFO[ListItem.Label]</label>
                        <font>atv_key</font><textcolor>E6FFFFFF</textcolor>
                        <align>center</align><aligny>center</aligny>
                        <visible>!Control.HasFocus(8200)</visible>
                    </control>
                </control>
            </focusedlayout>
            <content>
{key_items}
            </content>
        </control>

        <control type="group">
            <left>90</left><top>866</top>
{key_button(8204, 0, 516, "Type with keyboard", "keyboard", "                <onup>8200</onup><onright>8130</onright>")}
        </control>

        <!-- ===================== RIGHT: RESULTS ===================== -->

        <!-- People: "Explore titles related to" -->
        <control type="label">
            <left>700</left><top>56</top><width>1100</width><height>40</height>
            <label>$VAR[ATV_SearchPeopleHeader]</label>
            <font>atv_row</font><textcolor>FFFFFFFF</textcolor>
        </control>
        <control type="list" id="8110">
            <left>680</left><top>92</top><width>1240</width><height>240</height>
            <orientation>horizontal</orientation>
            <scrolltime tween="cubic" easing="out">380</scrolltime>
            <onleft>8200</onleft>
            <ondown>8120</ondown>
            <!-- Picking a person swaps the Movies / TV rows to their filmography -->
            <onclick>Skin.SetString(SearchPersonID,$INFO[Container(8110).ListItem.UniqueID(tmdb)])</onclick>
            <onclick>Skin.SetString(SearchPersonName,$ESCINFO[Container(8110).ListItem.Label])</onclick>
            <onclick>SetFocus(8120,0,absolute)</onclick>
            <itemlayout width="176" height="240">
                <control type="image">
                    <left>24</left><top>20</top><width>128</width><height>128</height>
                    <texture colordiffuse="FF2C2C2E" diffuse="atv/mask_circle.png">white.png</texture>
                </control>
                <control type="label">
                    <left>24</left><top>20</top><width>128</width><height>128</height>
                    <label>$INFO[ListItem.Label]</label>
                    <font>atv_meta</font><textcolor>99FFFFFF</textcolor>
                    <align>center</align><aligny>center</aligny>
                    <visible>String.IsEmpty(ListItem.Art(profile)) + String.IsEmpty(ListItem.Art(poster)) + String.IsEmpty(ListItem.Art(thumb))</visible>
                </control>
                <control type="image">
                    <left>24</left><top>20</top><width>128</width><height>128</height>
                    <aspectratio aligny="top" scalediffuse="false">scale</aspectratio>
                    <texture background="true" diffuse="atv/mask_circle.png">$VAR[ATV_PersonArt]</texture>
                </control>
                <control type="label">
                    <left>0</left><top>160</top><width>176</width><height>32</height>
                    <label>$INFO[ListItem.Label]</label>
                    <font>atv_small</font><textcolor>B3FFFFFF</textcolor>
                    <align>center</align>
                </control>
            </itemlayout>
            <focusedlayout width="176" height="240">
                <control type="group">
                    <include content="ATV_Lift"><param name="center" value="88,84" /><param name="zoom" value="110" /></include>
                    <control type="image">
                        <left>-12</left><top>-8</top><width>200</width><height>200</height>
                        <texture border="64">atv/shadow.png</texture>
                        <animation effect="fade" start="0" end="100" time="200">Focus</animation>
                        <animation effect="fade" start="100" end="0" time="150">Unfocus</animation>
                    </control>
                    <control type="image">
                        <left>24</left><top>20</top><width>128</width><height>128</height>
                        <texture colordiffuse="FF2C2C2E" diffuse="atv/mask_circle.png">white.png</texture>
                    </control>
                    <control type="label">
                        <left>24</left><top>20</top><width>128</width><height>128</height>
                        <label>$INFO[ListItem.Label]</label>
                        <font>atv_meta</font><textcolor>99FFFFFF</textcolor>
                        <align>center</align><aligny>center</aligny>
                        <visible>String.IsEmpty(ListItem.Art(profile)) + String.IsEmpty(ListItem.Art(poster)) + String.IsEmpty(ListItem.Art(thumb))</visible>
                    </control>
                    <control type="image">
                        <left>24</left><top>20</top><width>128</width><height>128</height>
                        <aspectratio aligny="top" scalediffuse="false">scale</aspectratio>
                        <texture background="true" diffuse="atv/mask_circle.png">$VAR[ATV_PersonArt]</texture>
                    </control>
                    <control type="label">
                        <left>0</left><top>160</top><width>176</width><height>32</height>
                        <label>$INFO[ListItem.Label]</label>
                        <font>atv_caption</font><textcolor>FFFFFFFF</textcolor>
                        <align>center</align>
                        <scroll>true</scroll>
                    </control>
                </control>
            </focusedlayout>
            <content target="videos">$VAR[ATV_SearchPeoplePath]</content>
        </control>

{poster_row(8120, 346, "ATV_SearchMoviesHeader", "ATV_SearchMoviesPath", "            <onleft>8200</onleft>\n            <onup>8110</onup>\n            <ondown>8130</ondown>")}

{poster_row(8130, 704, "ATV_SearchTVHeader", "ATV_SearchTVPath", "            <onleft>8200</onleft>\n            <onup>8120</onup>")}

        <!-- Nothing found -->
        <control type="label">
            <left>700</left><top>420</top><width>1100</width><height>120</height>
            <label>No results for “$INFO[Skin.String(SearchQuery)]”[CR][COLOR 80FFFFFF]Try a different title or an actor's name.[/COLOR]</label>
            <font>atv_row</font><textcolor>FFFFFFFF</textcolor>
            <visible>$EXP[ATV_SearchHasQuery] + !Container(8110).IsUpdating + !Container(8120).IsUpdating + !Container(8130).IsUpdating + Integer.IsEqual(Container(8110).NumItems,0) + Integer.IsEqual(Container(8120).NumItems,0) + Integer.IsEqual(Container(8130).NumItems,0)</visible>
        </control>

    </controls>
</window>
'''

# 1120 is the Search tab. 1121 is the same screen opened from a title page's cast row, so
# Kodi's Back returns to that title (Kodi rewinds history if a window is already in it).
# Each keeps its own skin strings (suffix '' / 'B') so they never overwrite each other.
WINDOWS = {
    1120: {'suffix': '', 'default': 8200,
           # Fresh from the Search tab: start on the keyboard (Back from a title keeps your place)
           'onload': '    <onload condition="Window.Previous(home)">SetFocus(8200)</onload>'},
    1121: {'suffix': 'B', 'default': 8120, 'onload': ''},
}
STRINGS = r'(Skin\.(?:String|SetString|Reset)\()(SearchQueryURL|SearchQuery|SearchPersonID|SearchPersonName)\b'
NAMES = r'(\$(?:VAR|EXP)\[|<(?:variable|expression) name=")(ATV_Search(?:HasQuery|HasPerson|PeoplePath|MoviesPath|TVPath|PeopleHeader|MoviesHeader|TVHeader))\b'


def suffixed(text, suffix):
    text = re.sub(STRINGS, lambda m: m.group(1) + m.group(2) + suffix, text)
    return re.sub(NAMES, lambda m: m.group(1) + m.group(2) + suffix, text)


with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'search_variables_template.xml')) as f:
    variables = f.read()
includes = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<!-- GENERATED by tools/gen_search.py from tools/search_variables_template.xml -->', '<includes>']
for window_id, cfg in WINDOWS.items():
    page = (xml.replace('{WINDOW_ID}', str(window_id)).replace('{DEFAULT}', str(cfg['default']))
            .replace('{ONLOAD}', cfg['onload']))
    with open(f'{OUT}/xml/Custom_{window_id}.xml', 'w') as f:
        f.write(suffixed(page, cfg['suffix']))
    includes.append(f'\t<!-- ===== Search window {window_id} ===== -->')
    includes.append(suffixed(variables, cfg['suffix']))
includes.append('</includes>\n')
with open(f'{OUT}/xml/Includes_ATV_Search.xml', 'w') as f:
    f.write('\n'.join(includes))
print('ok')
