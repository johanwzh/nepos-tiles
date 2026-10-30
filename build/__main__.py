"""python -m build <extract.osm.pbf> <out dir> [--bbox minlon,minlat,maxlon,maxlat]"""
import argparse
import gzip
import hashlib
import json
import os
import sys
import time

from build.encode import encode
from build.graph import TILE_LAT, TILE_LON, build_tiles
from build.read import Q, Network, read


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


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -m build', description='OSM extract -> NPT2 road tiles + manifest')
    ap.add_argument('extract')
    ap.add_argument('out')
    ap.add_argument('--bbox', help='minlon,minlat,maxlon,maxlat: keep only ways with a node inside')
    args = ap.parse_args(argv)

    t0 = time.time()
    net = read(args.extract)
    if args.bbox:
        net = _in_bbox(net, [float(v) for v in args.bbox.split(',')])
    t1 = time.time()
    print(f'read {len(net.ways)} ways in {t1 - t0:.0f} s')
    tiles = build_tiles(net)
    print(f'{len(tiles)} tiles, {sum(len(t.edges) for t in tiles.values())} edges in {time.time() - t1:.0f} s')
    print('stats', json.dumps(net.stats, sort_keys=True))

    os.makedirs(args.out, exist_ok=True)
    manifest = {'format': 'NPT2', 'set': 'road', 'built': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'dataDate': net.data_date, 'source': os.path.basename(args.extract),
                'tileLon': TILE_LON, 'tileLat': TILE_LAT, 'q': Q, 'tiles': {}}
    for (ix, iy), tile in sorted(tiles.items()):
        gz = gzip.compress(encode(tile), 9, mtime=0)
        key = f'{ix}_{iy}'
        with open(os.path.join(args.out, f'{key}.bin.gz'), 'wb') as f:
            f.write(gz)
        manifest['tiles'][key] = {'size': len(gz), 'hash': hashlib.sha1(gz).hexdigest()[:12]}
    with open(os.path.join(args.out, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)

    sizes = sorted(v['size'] for v in manifest['tiles'].values()) or [0]
    peak = _peak_memory_mb()
    print(f'{len(tiles)} tiles, {sum(sizes) / 1e6:.1f} MB; tile KB median {sizes[len(sizes) // 2] / 1e3:.0f}, '
          f'p90 {sizes[int(len(sizes) * .9)] / 1e3:.0f}, max {sizes[-1] / 1e3:.0f}; {time.time() - t0:.0f} s'
          + (f'; peak memory {peak:.0f} MB' if peak else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
