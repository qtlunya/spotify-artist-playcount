# spotify-artist-playcount

This script retrieves total play count for an artist on Spotify, making use of the Spotify Web API to look up artists and their albums, and the [unofficial play count API by evilarceus](https://github.com/evilarceus/Spotify-PlayCount).

## Usage
You can specify one or more Spotify artist IDs/URIs separated by spaces. To search by name, prefix the artists with `-s`.

Examples:
```sh
$ ./artistplaycount.py "74KM79TiuVKeVCqs8QtB0B"
$ ./artistplaycount.py "spotify:artist:74KM79TiuVKeVCqs8QtB0B"
$ ./artistplaycount.py "https://open.spotify.com/artist/74KM79TiuVKeVCqs8QtB0B"
$ ./artistplaycount.py -s "sabrina carpenter"
$ ./artistplaycount.py -s "loona" -s "loona 1/3" -s "odd eye circle" -s "yyxy"
$ ./artistplaycount.py -s "loona" "1Pml984JKCN83PxCBSVSvf" "5KPaeBm0fVfCSZLydp9jdy" "4JKDJj0bOTw07GrQ9pmcUS"
```
