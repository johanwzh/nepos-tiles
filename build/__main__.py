"""python -m build <extract.osm.pbf> <out root> [--sets road,rail,...] [--bbox minlon,minlat,maxlon,maxlat]

Each set (road, rail, tram, metro, ferry, cable; all by default) is written to <out root>/<set>/: its tiles and a
manifest naming the set."""
import argparse
import gzip
import hashlib
import json
import os
import sys
import time

from build.derive import SETS
from build.encode import encode
from build.graph import TILE_LAT, TILE_LON, build_tiles
from build.read import Q, Network, read_sets


def _in_bbox(net, bbox):
    x0, y0, x1, y1 = (round(v * Q) for v in bbox)
    ways = [w for w in net.ways if any(x0 <= x <= x1 and y0 <= y <= y1 for x, y in zip(w[4], w[5]))]
    return Network(ways, net.restrictions, net.stats, net.data_date)


def _peak_memory_mb():
    try:
        import resource
    except ImportError:                           # Windows
        return None
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def _write_set(name, net, out, source):
    """Tiles and manifest of one set; returns the summary line."""
    t0 = time.time()
    tiles = build_tiles(net)
    os.makedirs(out, exist_ok=True)
    manifest = {'format': 'NPT2', 'set': name, 'built': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'dataDate': net.data_date, 'source': source,
                'tileLon': TILE_LON, 'tileLat': TILE_LAT, 'q': Q, 'tiles': {}}
    for (ix, iy), tile in sorted(tiles.items()):
        gz = gzip.compress(encode(tile), 9, mtime=0)
        key = f'{ix}_{iy}'
        with open(os.path.join(out, f'{key}.bin.gz'), 'wb') as f:
            f.write(gz)
        manifest['tiles'][key] = {'size': len(gz), 'hash': hashlib.sha1(gz).hexdigest()[:12]}
    with open(os.path.join(out, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)
    sizes = sorted(v['size'] for v in manifest['tiles'].values()) or [0]
    return (f'{name}: {len(net.ways)} ways, {len(tiles)} tiles, {sum(len(t.edges) for t in tiles.values())} edges, '
            f'{sum(sizes) / 1e6:.1f} MB; tile KB median {sizes[len(sizes) // 2] / 1e3:.0f}, '
            f'p90 {sizes[int(len(sizes) * .9)] / 1e3:.0f}, max {sizes[-1] / 1e3:.0f}; {time.time() - t0:.0f} s; '
            f'stats {json.dumps(net.stats, sort_keys=True)}')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -m build', description='OSM extract -> NPT2 tiles + manifest per set')
    ap.add_argument('extract')
    ap.add_argument('out', help='out root: each set goes in <out>/<set>/')
    ap.add_argument('--sets', default=','.join(SETS), help=f'comma-separated, of {",".join(SETS)}')
    ap.add_argument('--bbox', help='minlon,minlat,maxlon,maxlat: keep only ways with a node inside')
    args = ap.parse_args(argv)
    sets = [s for s in args.sets.split(',') if s]
    unknown = [s for s in sets if s not in SETS]
    if unknown:
        ap.error(f'unknown set(s): {",".join(unknown)}')

    t0 = time.time()
    nets = read_sets(args.extract, tuple(sets))
    print(f'read {sum(len(n.ways) for n in nets.values())} ways in {time.time() - t0:.0f} s')
    for name in sets:
        net = nets[name]
        if args.bbox:
            net = _in_bbox(net, [float(v) for v in args.bbox.split(',')])
        print(_write_set(name, net, os.path.join(args.out, name), os.path.basename(args.extract)))
    peak = _peak_memory_mb()
    print(f'done in {time.time() - t0:.0f} s' + (f'; peak memory {peak:.0f} MB' if peak else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
