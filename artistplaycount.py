#!/usr/bin/env python3

import argparse
import json
import re
import sys
import time

import colorama
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from termcolor import colored

colorama.init(autoreset=True)

parser = argparse.ArgumentParser()
parser.add_argument('artist', nargs='*', help='Spotify ID of the artists(s)')
parser.add_argument('-s', '--search', default=[], action='append', help='artist name(s) to search for')
parser.add_argument('-a', '--album', help='search for specific album(s) only')
parser.add_argument('-t', '--track', help='search for specific track(s) only')
parser.add_argument('-c', '--country', help='country code to retrieve results from')
parser.add_argument('--types', type=lambda x: x.split(','), default=['album', 'single'])  # album, single, compilation
parser.add_argument('--features', action='store_true', help='include albums where the artist is featured')
parser.add_argument('--no-skip', action='store_true', help='do not skip duplicate songs')
parser.add_argument('--slow', action='store_true', help='add delay between printing lines')
args = parser.parse_args()

session = requests.Session()
adapter = HTTPAdapter(max_retries=Retry(total=5, backoff_factor=1, status_forcelist=[500]))
session.mount('http://', adapter)
session.mount('https://', adapter)

with open('config.json') as fd:
    config = json.load(fd)


def log(*func_args, **kwargs):
    print(colored(*func_args, **kwargs), file=sys.stderr)

    if args.slow:
        time.sleep(0.2)


def get_access_token():
    r = session.post('https://accounts.spotify.com/api/token',
                     data={'grant_type': 'client_credentials'},
                     auth=(config['client_id'], config['client_secret']))
    r.raise_for_status()

    data = r.json()

    data['expires_time'] = time.time() + data['expires_in']

    session.headers['Authorization'] = f'Bearer {data["access_token"]}'

    with open('auth.json', 'w') as fd:
        json.dump(data, fd)


try:
    with open('auth.json') as fd:
        auth_data = json.load(fd)
        session.headers['Authorization'] = f'Bearer {auth_data["access_token"]}'
except (FileNotFoundError, json.JSONDecodeError):
    log('Getting access token')
    get_access_token()
else:
    if auth_data['expires_time'] <= time.time():
        log(colored('Access token expired, refreshing', 'yellow'))
        get_access_token()
    else:
        log('Using saved access token')


def get_albums(artist_id, country_code, offset=0, albums=[]):
    log(f'Getting albums ({offset}-{offset + 50})...')

    r = session.get(f'https://api.spotify.com/v1/artists/{artist_id}/albums',
                    params={
                        'country': country_code,
                        'include_groups': 'album,single,appears_on' if args.features else 'album,single',
                        'limit': 50,
                        'offset': offset,
                    })
    data = r.json()

    if r.status_code == 401:
        log(colored('Access token expired, refreshing', 'yellow'))
        get_access_token()
        return get_albums(artist_id, country_code, offset, albums)

    r.raise_for_status()

    for album in data['items']:
        albums.append(album)

    if data['next']:
        return get_albums(artist_id, country_code, offset + 50, albums)

    return albums


artist_playcount = 0
seen_albums = set()
seen_tracks = set()
playcounts = set()

artists = set()

if not args.artist and not args.search:
    log('No artists specified.', 'red')
    sys.exit(1)

for arg in args.artist:
    m = re.match(r'(?i)(?:https?://open\.spotify\.com/artist/|spotify:artist:)?([a-z0-9]{22})', arg)
    if m:
        artists.add(m.group(1))
    else:
        log(f'Invalid Spotify artist ID: {arg!r}. Use the -s option to search by artist name.', 'red')
        sys.exit(1)

for arg in args.search:
    log(f'Searching for artist {arg!r}...')

    r = session.get('https://api.spotify.com/v1/search', params={
        'q': arg,
        'type': 'artist',
        'market': args.country,
        'limit': 1,
    })

    data = r.json()

    if 'error' in data:
        err = data['error']
        log(colored(f'Error: ({err["status"]}) {err["message"]}'), 'red')
        sys.exit(1)

    if not data.get('artists', {}).get('items'):
        log(colored(f'Artist {arg!r} not found.', 'red'))
        sys.exit(1)

    artist = data['artists']['items'][0]['uri'].split(':')[-1]
    artists.add(artist)

for artist in artists:
    albums = get_albums(artist, args.country)

    log('')

    for album in albums:
        if album['id'] in seen_albums:
            continue

        if album['album_type'] not in args.types:
            continue

        if args.album and args.album.lower() not in album['name'].lower():
            continue

        seen_albums.add(album['id'])

        album_playcount = 0

        log(f'Getting playcounts for {colored(album["name"], "cyan")} ({album["album_type"]})...', attrs=['bold'])

        r = session.get(config['playcount_api_url'], params={'albumid': album['id']})
        r.raise_for_status()
        data = r.json()

        print(album['album_group'], album['album_type'])

        for disc in data['data']['discs']:
            for track in disc['tracks']:
                if not (any(x for x in album['artists'] if x['uri'] == f'spotify:artist:{artist}') or
                        any(x for x in track['artists'] if x['uri'] == f'spotify:artist:{artist}')):
                    continue

                if args.track and args.track.lower() not in track['name'].lower():
                    continue

                if ((not args.no_skip) and
                        (track['uri'] in seen_tracks or track['playcount'] in playcounts)):
                    log(f'* Skipping {track["name"]!r}, already seen before', 'yellow')
                    continue

                seen_tracks.add(track['uri'])
                playcounts.add(track['playcount'])

                fmt_playcount = '{:,d}'.format(track['playcount'])
                color_playcount = colored(fmt_playcount, 'yellow', attrs=['bold'])
                log(f'* {track["name"]}: {color_playcount}')

                artist_playcount += track['playcount']
                album_playcount += track['playcount']

        if album_playcount:
            fmt_playcount = '{:,d}'.format(album_playcount)
            color_playcount = colored(fmt_playcount, 'red', attrs=['bold'])
            log(f'Total: {color_playcount}', attrs=['bold'])
        else:
            log('No new songs found on album', attrs=['bold'])

        log('')

fmt_playcount = '{:,d}'.format(artist_playcount)
color_playcount = colored(fmt_playcount, 'green', attrs=['bold'])
log(f'Artist total: {color_playcount}')
