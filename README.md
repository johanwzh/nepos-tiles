# nepos-tiles

Graph tiles for the routing in [Nepos](https://github.com/johanwzh/nepos-online), built from OpenStreetMap.

A GitHub Action takes Geofabrik's Norway extract every month (and on demand) and writes one set of small binary tiles
(format `NPT2`) plus a manifest per network to GitHub Pages:

| Set | OSM ways |
|---|---|
| `road` | the roads a bus may use, and the car ferries (with the bus turn restrictions) |
| `rail` | `railway=rail`, `narrow_gauge` |
| `tram` | `railway=tram`, `light_rail` |
| `metro` | `railway=subway`, `light_rail` |
| `ferry` | every `route=ferry` way, and every way of a `route=ferry` relation |
| `cable` | the aerialways that carry people, `railway=funicular` |

Disused, abandoned, proposed and similar ways are left out.

- `https://johanwzh.github.io/nepos-tiles/<set>/manifest.json`
- `https://johanwzh.github.io/nepos-tiles/<set>/{ix}_{iy}.bin.gz` — gzip bytes; Nepos decompresses them itself.

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
python -m build <extract.osm.pbf> <out root> [--sets road,rail,tram,metro,ferry,cable] [--bbox minlon,minlat,maxlon,maxlat]
```

`--bbox` keeps only the ways with a node inside the box (small test sets). The command prints the counts, tile sizes,
time and, on Linux, peak memory.
