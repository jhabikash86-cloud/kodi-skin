# -*- coding: utf-8 -*-
"""Home's Browse by Mood: each mood's name and the TMDb Helper lists behind its page.

One list here, read by tools/gen_browse.py (the tiles, and the mood page's rows) and by
extras/charts.py (three posters for each tile, weekly, so Home asks for nothing more).
Paths use the date tokens extras/dates.py keeps current; documentaries, cartoons and
comedies stay out, as they do across the skin.
"""
PLUGIN = 'plugin://plugin.video.themoviedb.helper/?'
DECADE = '$INFO[Skin.String(ATVDate.d3650)]'
THREE_YEARS = '$INFO[Skin.String(ATVDate.d1095)]'
NOT_SERIALS = '10766,10763,10767,10764,10762'
TRUE_STORY = '9672'


def discover(kind, query):
    return f'{PLUGIN}info=discover&tmdb_type={kind}&{query}&with_id=True&hide_unaired=true&nextpage=false'


# key -> (name, movies list, series list)
MOODS = {
    'truecrime': ('True Crime',
                  discover('movie', f'with_keywords={TRUE_STORY}&with_genres=80&without_genres=99,16,35&vote_count.gte=150&sort_by=popularity.desc'),
                  discover('tv', f'with_keywords={TRUE_STORY}&with_genres=80&without_genres=99,16,35,{NOT_SERIALS}&vote_count.gte=50&sort_by=popularity.desc')),
    'thrillers': ('Edge-of-Seat Thrillers',
                  discover('movie', f'with_genres=53&without_genres=16,35,10751,27&primary_release_date.gte={THREE_YEARS}&vote_count.gte=300&sort_by=popularity.desc'),
                  discover('tv', f'with_genres=80%7C9648&without_genres=16,35,99,{NOT_SERIALS}&first_air_date.gte={THREE_YEARS}&vote_count.gte=100&sort_by=popularity.desc')),
    'horror': ('Horror Night',
               discover('movie', f'with_genres=27&without_genres=16,35,10751&primary_release_date.gte={DECADE}&vote_count.gte=300&sort_by=popularity.desc'),
               f'{PLUGIN}info=trakt_mostviewers&tmdb_type=tv&genres=horror,-anime,-animation,-comedy&ratings=70-100&nextpage=false'),
    'bollywood': ('Bollywood Blockbusters',
                  discover('movie', f'with_original_language=hi&without_genres=99,16&primary_release_date.gte={DECADE}&vote_count.gte=150&sort_by=popularity.desc'),
                  discover('tv', f'with_original_language=hi&without_genres=99,16,35,{NOT_SERIALS}&first_air_date.gte={DECADE}&vote_count.gte=30&sort_by=popularity.desc')),
    'tamil': ('Tamil Hits',
              discover('movie', f'with_original_language=ta&without_genres=99,16&primary_release_date.gte={DECADE}&vote_count.gte=60&sort_by=popularity.desc'),
              discover('tv', f'with_original_language=ta&without_genres=99,16,{NOT_SERIALS}&first_air_date.gte={DECADE}&vote_count.gte=5&sort_by=popularity.desc')),
    'truestories': ('Based on True Stories',
                    discover('movie', f'with_keywords={TRUE_STORY}&without_genres=99,16,10751,35&primary_release_date.gte={DECADE}&vote_count.gte=300&sort_by=popularity.desc'),
                    discover('tv', f'with_keywords={TRUE_STORY}&without_genres=99,16,35,{NOT_SERIALS}&vote_count.gte=50&sort_by=popularity.desc')),
}
