"""Reference decoder for NPT2 tiles (tests only; Nepos has its own in JavaScript)."""
import struct


def _varint(buf, pos):
    shift = result = 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if b < 0x80:
            return (result >> 1) ^ -(result & 1), pos
        shift += 7


def decode(buf: bytes) -> dict:
    assert buf[:4] == b'NPT2'
    n_nodes, n_edges, n_attrs, names_bytes, points_bytes, n_restr = struct.unpack_from('<6I', buf, 4)
    pos = 28
    offsets = {}

    def align():
        nonlocal pos
        pos += -pos % 4

    def take(name, fmt, count, size):
        nonlocal pos
        offsets[name] = pos
        values = list(struct.unpack_from(f'<{count}{fmt}', buf, pos)) if count else []
        pos += count * size
        align()
        return values

    lon = take('lon', 'i', n_nodes, 4)
    lat = take('lat', 'i', n_nodes, 4)
    border = take('border', 'B', n_nodes, 1)
    offsets['attrs'] = pos
    attrs = [struct.unpack_from('<BBBBHHHH', buf, pos + 12 * i) for i in range(n_attrs)]
    pos += 12 * n_attrs
    offsets['names'] = pos
    names = buf[pos:pos + names_bytes].decode('utf-8').split('\n')
    pos += names_bytes
    align()
    e_from = take('from', 'I', n_edges, 4)
    e_to = take('to', 'I', n_edges, 4)
    e_len = take('length', 'f', n_edges, 4)
    e_attr = take('attr', 'H', n_edges, 2)
    e_name = take('name', 'I', n_edges, 4)
    e_way = take('way', 'I', n_edges, 4)
    e_off = take('offset', 'I', n_edges, 4)
    e_cnt = take('count', 'H', n_edges, 2)
    offsets['points'] = pos
    points = buf[pos:pos + points_bytes]
    pos += points_bytes
    align()
    offsets['restrictions'] = pos
    restrictions = [struct.unpack_from('<IIIB', buf, pos + 16 * i) for i in range(n_restr)]
    pos += 16 * n_restr
    assert pos == len(buf), (pos, len(buf))

    edges = []
    for e in range(n_edges):
        x, y = lon[e_from[e]], lat[e_from[e]]
        p, pts = e_off[e], []
        for _ in range(e_cnt[e]):
            dx, p = _varint(points, p)
            dy, p = _varint(points, p)
            x, y = x + dx, y + dy
            pts.append((x, y))
        edges.append({'from': e_from[e], 'to': e_to[e], 'length': e_len[e], 'attr': e_attr[e],
                      'name': e_name[e], 'way': e_way[e], 'points': pts})
    nodes = [(lon[i], lat[i], border[i]) for i in range(n_nodes)]
    return {'nodes': nodes, 'edges': edges, 'attrs': attrs, 'names': names, 'restrictions': restrictions,
            'offsets': offsets}
