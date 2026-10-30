import math

from build.graph import build_tiles, haversine
from build.read import Q
from tests.helpers import network, way

LAT = 59.91          # tile row 479 (59.875 .. 60.0)


def all_edges(tiles):
    return [(k, e) for k, t in tiles.items() for e in t.edges]


def border_nodes(t):
    return {n for n in t.nlist if n[2]}


def test_splits_at_junctions():
    a = way(1, [(10.01, LAT), (10.02, LAT), (10.03, LAT)], [1, 2, 3])
    b = way(2, [(10.02, LAT - 0.01), (10.02, LAT), (10.02, LAT + 0.01)], [4, 2, 5])
    tiles = build_tiles(network([a, b]))
    assert list(tiles) == [(40, 479)]
    t = tiles[(40, 479)]
    assert len(t.edges) == 4
    assert len(t.nlist) == 5
    assert ('n', 2) in t.nodes


def test_cuts_at_the_grid_and_shares_the_border_node():
    tiles = build_tiles(network([way(1, [(10.24, LAT), (10.26, LAT)])]))
    assert sorted(tiles) == [(40, 479), (41, 479)]
    left, right = tiles[(40, 479)], tiles[(41, 479)]
    assert len(left.edges) == len(right.edges) == 1
    assert border_nodes(left) == border_nodes(right) == {(round(10.25 * Q), round(LAT * Q), 1)}


def test_road_along_a_border_crossing_it_three_times():
    line = 59.875
    zigzag = [(10.01, line + 0.001), (10.02, line - 0.001), (10.03, line + 0.001), (10.04, line - 0.001)]
    tiles = build_tiles(network([way(1, zigzag)]))
    edges = sorted(all_edges(tiles), key=lambda ke: ke[1].points[0][0])
    assert [k for k, _ in edges] == [(40, 479), (40, 478), (40, 479), (40, 478)]
    assert all(e.length > 1 for _, e in edges)
    up, down = tiles[(40, 479)], tiles[(40, 478)]
    assert border_nodes(up) == border_nodes(down)
    assert len(border_nodes(up)) == 3


def test_node_exactly_on_a_grid_line_is_a_border_node():
    tiles = build_tiles(network([way(1, [(10.24, LAT), (10.25, LAT), (10.26, LAT)])]))
    assert sorted(tiles) == [(40, 479), (41, 479)]
    for t in tiles.values():
        assert border_nodes(t) == {(round(10.25 * Q), round(LAT * Q), 1)}


def test_lengths_sum_to_the_way_length():
    coords = [(10.20, 59.86), (10.27, 59.88), (10.31, 59.90), (10.52, 59.99)]
    tiles = build_tiles(network([way(1, coords)]))
    expected = sum(haversine(*coords[i], *coords[i + 1]) for i in range(len(coords) - 1))
    assert len(tiles) > 2
    assert math.isclose(sum(e.length for _, e in all_edges(tiles)), expected, abs_tol=0.1)


def test_repeated_points_dropped():
    tiles = build_tiles(network([way(1, [(10.01, LAT), (10.01, LAT), (10.02, LAT)])]))
    (_, e), = all_edges(tiles)
    assert e.points == [(round(10.01 * Q), round(LAT * Q)), (round(10.02 * Q), round(LAT * Q))]
