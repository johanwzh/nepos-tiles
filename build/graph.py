"""Split ways into edges at junctions, cut them at the tile grid and group them by tile."""
import math
from collections import defaultdict

from build.read import Q

TILE_LON, TILE_LAT = 0.25, 0.125              # ~14 x 14 km at 60 N
GRID_X, GRID_Y = round(TILE_LON * Q), round(TILE_LAT * Q)


def haversine(lon1, lat1, lon2, lat2):
    r, d = 6371008.8, math.pi / 180
    a = math.sin((lat2 - lat1) * d / 2) ** 2 + math.cos(lat1 * d) * math.cos(lat2 * d) * math.sin((lon2 - lon1) * d / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def on_grid(qlon, qlat):
    return qlon % GRID_X == 0 or qlat % GRID_Y == 0


def tile_of(qlon, qlat):
    return qlon // GRID_X, qlat // GRID_Y


class Edge:
    __slots__ = ('a', 'b', 'length', 'attr', 'name', 'way_id', 'points', 'ka', 'kb')

    def __init__(self, a, b, length, attr, name, way_id, points, ka, kb):
        self.a, self.b, self.length, self.attr, self.name = a, b, length, attr, name
        self.way_id, self.points, self.ka, self.kb = way_id, points, ka, kb


class Tile:
    """Nodes are keyed ('n', osm id) or ('b', qlon, qlat) for a cut on a grid line; nlist holds (qlon, qlat, flags):
    bit 0 on the tile border, bit 1 a level crossing of tracks (no turning from one track to the other)."""

    def __init__(self, crossings=frozenset()):
        self.crossings = crossings
        self.nodes, self.nlist, self.edges = {}, [], []
        self.attrs, self.names = {}, {}
        self.restrictions = []                 # (from_edge, via_node, to_edge, only), local indices

    def node(self, key, qlon, qlat):
        i = self.nodes.get(key)
        if i is None:
            i = self.nodes[key] = len(self.nlist)
            border = 1 if key[0] == 'b' or on_grid(qlon, qlat) else 0
            crossing = 2 if key[0] == 'n' and key[1] in self.crossings else 0
            self.nlist.append((qlon, qlat, border | crossing))
        return i

    def attr_list(self):
        return list(self.attrs)

    def name_list(self):
        return list(self.names)


def _length(pts):
    return sum(haversine(pts[i][0] / Q, pts[i][1] / Q, pts[i + 1][0] / Q, pts[i + 1][1] / Q) for i in range(len(pts) - 1))


def _crossings(p0, p1):
    """Fractions in (0, 1) where the segment p0-p1 crosses a grid line, with the crossing point."""
    (x0, y0), (x1, y1) = p0, p1
    hits = []
    for g in range(min(x0, x1) // GRID_X + 1, (max(x0, x1) - 1) // GRID_X + 1):
        f = (g * GRID_X - x0) / (x1 - x0)
        hits.append((f, (g * GRID_X, round(y0 + (y1 - y0) * f))))
    for g in range(min(y0, y1) // GRID_Y + 1, (max(y0, y1) - 1) // GRID_Y + 1):
        f = (g * GRID_Y - y0) / (y1 - y0)
        hits.append((f, (round(x0 + (x1 - x0) * f), g * GRID_Y)))
    return sorted(h for h in hits if 0 < h[0] < 1)


def build_tiles(net) -> dict:
    tiles = defaultdict(lambda: Tile(net.crossings))
    use = defaultdict(int)
    for _, _, _, ids, lons, lats in net.ways:
        last = len(ids) - 1
        for i, n in enumerate(ids):
            use[n] += 2 if i in (0, last) or on_grid(lons[i], lats[i]) else 1

    def emit(way_id, attr, name, pts, k0, k1):
        k = (len(pts) - 1) // 2
        t = tiles[tile_of((pts[k][0] + pts[k + 1][0]) // 2, (pts[k][1] + pts[k + 1][1]) // 2)]
        a, b = t.node(k0, *pts[0]), t.node(k1, *pts[-1])
        ai = t.attrs.setdefault(attr, len(t.attrs))
        ni = t.names.setdefault(name, len(t.names))
        t.edges.append(Edge(a, b, _length(pts), ai, ni, way_id, pts, k0, k1))

    def cut(way_id, attr, name, pts, k0, k1):
        piece, start = [pts[0]], k0
        for i in range(len(pts) - 1):
            for _, p in _crossings(pts[i], pts[i + 1]):
                if p == piece[-1] or p == pts[i + 1]:
                    continue
                piece.append(p)
                kb = ('b', *p)
                emit(way_id, attr, name, piece, start, kb)
                piece, start = [p], kb
            piece.append(pts[i + 1])
        emit(way_id, attr, name, piece, start, k1)

    for way_id, attr, name, ids, lons, lats in net.ways:
        s = 0
        for i in range(1, len(ids)):
            if i == len(ids) - 1 or use[ids[i]] > 1:
                pts = []
                for j in range(s, i + 1):
                    p = (lons[j], lats[j])
                    if not pts or p != pts[-1]:
                        pts.append(p)
                if len(pts) >= 2:
                    cut(way_id, attr, name, pts, ('n', ids[s]), ('n', ids[i]))
                s = i
    tiles = dict(tiles)
    _place_restrictions(net, tiles)
    return tiles


def _place_restrictions(net, tiles):
    """Point each restriction at the edges of its from/to ways that touch the via node, in the via node's tile.
    A from or to way that passes through the via node (two edges there) is ambiguous and skipped."""
    at = defaultdict(list)                        # (way id, via key) -> [(tile key, edge index)]
    wanted = {('n', r[1]) for r in net.restrictions}
    for tk, t in tiles.items():
        for i, e in enumerate(t.edges):
            for key in {e.ka, e.kb}:
                if key in wanted:
                    at[(e.way_id, key)].append((tk, i))
    stats = net.stats

    def count(name):
        stats[name] = stats.get(name, 0) + 1

    for from_way, via, to_way, only in net.restrictions:
        key = ('n', via)
        froms, tos = at[(from_way, key)], at[(to_way, key)]
        if not froms or not tos:
            count('restrictions_unmatched')
            continue
        if from_way == to_way:
            if only:
                count('restrictions_ambiguous')
                continue
            pairs = [(f, f) for f in froms]       # no U-turn back onto the same edge
        elif len(froms) > 1 or len(tos) > 1:
            count('restrictions_ambiguous')
            continue
        else:
            pairs = [(froms[0], tos[0])]
        placed = False
        for (ftk, fi), (ttk, ti) in pairs:
            if ftk == ttk:
                t = tiles[ftk]
                t.restrictions.append((fi, t.nodes[key], ti, only))
                placed = True
        if not placed:
            count('restrictions_cross_tile')
