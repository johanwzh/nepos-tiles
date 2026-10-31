import math

from build.encode import encode
from build.graph import build_tiles
from tests.decode import decode
from tests.helpers import network, way

LAT = 59.91


def tile():
    a = way(1, [(10.01, LAT), (10.015, LAT + 0.002), (10.02, LAT), (10.03, LAT)], [1, 6, 2, 3],
            attr=(1, 1, 60, 3.2, 2.55, 12.5, 3.5), name='Rv 4 / Storgata')
    b = way(2, [(10.02, LAT - 0.01), (10.02, LAT), (10.02, LAT + 0.01)], [4, 2, 5], name='Ærfuglveien')
    return build_tiles(network([a, b]))[(40, 479)]


def test_round_trip():
    t = tile()
    d = decode(encode(t))
    assert d['nodes'] == [(x, y, int(bool(b))) for x, y, b in t.nlist]
    assert len(d['edges']) == len(t.edges)
    names = t.name_list()
    for got, e in zip(d['edges'], t.edges):
        assert (got['from'], got['to'], got['way']) == (e.a, e.b, e.way_id)
        assert math.isclose(got['length'], e.length, rel_tol=1e-6)
        assert got['points'] == e.points[1:-1]
        assert d['names'][got['name']] == names[e.name]
    assert (1, 1, 60, 0, 320, 255, 125, 35) in d['attrs']
    assert 'Ærfuglveien' in d['names']


def test_sections_are_4_byte_aligned():
    d = decode(encode(tile()))
    assert all(off % 4 == 0 for off in d['offsets'].values())


def test_ferry_flag():
    t = build_tiles(network([way(1, [(10.01, LAT), (10.02, LAT)], attr=(4, 0, 0, 0, 0, 0, 0))]))[(40, 479)]
    assert decode(encode(t))['attrs'] == [(4, 0, 0, 1, 0, 0, 0, 0)]


def test_a_level_crossing_is_flagged_in_the_node_byte():
    """Bit 0 of the node byte: on a tile border; bit 1: tracks cross here without a link (final review 2026-11-01)."""
    a = way(1, [(10.01, LAT), (10.02, LAT), (10.03, LAT)], [1, 9, 3], attr=(0, 0, 0, 0, 0, 0, 0))
    b = way(2, [(10.02, LAT - 0.01), (10.02, LAT), (10.02, LAT + 0.01)], [4, 9, 5], attr=(0, 0, 0, 0, 0, 0, 0))
    t = build_tiles(network([a, b])._replace(crossings=frozenset({9})))[(40, 479)]
    flags = {(n[0], n[1]): n[2] for n in decode(encode(t))['nodes']}
    assert flags[(round(10.02 * 1e7), round(LAT * 1e7))] == 2
    assert sorted(set(flags.values())) == [0, 2]
