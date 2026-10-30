import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from tests.decode import decode

ROOT = Path(__file__).parent.parent
SMALL = ROOT / 'tests' / 'fixtures' / 'small.osm'


def run(*args):
    return subprocess.run([sys.executable, '-m', 'build', *map(str, args)], cwd=ROOT, check=True,
                          capture_output=True, text=True)


def test_build_writes_tiles_and_manifest(tmp_path):
    out = tmp_path / 'road'
    result = run(SMALL, out)
    assert 'tiles' in result.stdout
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['format'] == 'NPT2'
    assert manifest['set'] == 'road'
    assert manifest['source'] == 'small.osm'
    assert manifest['dataDate'] == ''
    assert manifest['built'].endswith('Z')
    assert (manifest['tileLon'], manifest['tileLat'], manifest['q']) == (0.25, 0.125, 10_000_000)
    assert manifest['tiles']
    edges = 0
    for key, info in manifest['tiles'].items():
        gz = (out / f'{key}.bin.gz').read_bytes()
        assert len(gz) == info['size']
        assert hashlib.sha1(gz).hexdigest()[:12] == info['hash']
        edges += len(decode(gzip.decompress(gz))['edges'])
    assert edges > 0


def test_bbox_keeps_ways_with_a_node_inside(tmp_path):
    out = tmp_path / 'road'
    run(SMALL, out, '--bbox', '9.99,59.89,10.005,59.915')        # around nodes 1 and 11 only
    manifest = json.loads((out / 'manifest.json').read_text())
    ways = set()
    for key in manifest['tiles']:
        ways |= {e['way'] for e in decode(gzip.decompress((out / f'{key}.bin.gz').read_bytes()))['edges']}
    assert ways == {100, 101, 103}
