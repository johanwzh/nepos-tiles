# nepos-tiles

Road graph tiles for the routing in [Nepos](https://github.com/johanwzh/nepos-online), built from OpenStreetMap.

A GitHub Action takes Geofabrik's Norway extract every month (and on demand), keeps the roads a bus may use and the
car ferries, and writes small binary tiles (format `NPT2`) plus a manifest to GitHub Pages:

- `https://johanwzh.github.io/nepos-tiles/road/manifest.json`
- `https://johanwzh.github.io/nepos-tiles/road/{ix}_{iy}.bin.gz` — gzip bytes; Nepos decompresses them itself.

The grid is 0.25° longitude × 0.125° latitude: `ix = floor(lon / 0.25)`, `iy = floor(lat / 0.125)`.

## Data licence

Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), available under the
[Open Database Licence (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/). The tiles are a derived database
under the same licence. The code in this repository is MIT licensed (see `LICENSE`).

## Local build

Python 3.12 or later.

```
pip install -r requirements.txt
python -m pytest -q
python -m build <extract.osm.pbf> <out dir>
```
