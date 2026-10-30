"""Write one tile in the NPT2 binary layout (little-endian, every section on a 4-byte boundary)."""
import array
import struct

from build.derive import FERRY_CLASS

U16 = 0xFFFF


def _u16(value, scale):
    return min(round(value * scale), U16)


def _zigzag_varint(out, v):
    v = (v << 1) ^ (v >> 63)
    while v >= 0x80:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v)


def _pad(out):
    out += b'\0' * (-len(out) % 4)


def encode(tile) -> bytes:
    nl, edges, attrs = tile.nlist, tile.edges, tile.attr_list()
    names = '\n'.join(tile.name_list()).encode('utf-8')
    points = bytearray()
    offsets, counts = array.array('I'), array.array('H')
    for e in edges:
        offsets.append(len(points))
        counts.append(len(e.points) - 2)
        px, py = e.points[0]
        for x, y in e.points[1:-1]:
            _zigzag_varint(points, x - px)
            _zigzag_varint(points, y - py)
            px, py = x, y

    out = bytearray(b'NPT2')
    out += struct.pack('<6I', len(nl), len(edges), len(attrs), len(names), len(points), len(tile.restrictions))
    out += array.array('i', (n[0] for n in nl)).tobytes()
    out += array.array('i', (n[1] for n in nl)).tobytes()
    out += bytes(n[2] for n in nl)
    _pad(out)
    for cls, d, speed, mh, mw, ml, mt in attrs:
        out += struct.pack('<BBBBHHHH', cls, d, min(speed, 255), 1 if cls == FERRY_CLASS else 0,
                           _u16(mh, 100), _u16(mw, 100), _u16(ml, 10), _u16(mt, 10))
    out += names
    _pad(out)
    for code, values in (('I', (e.a for e in edges)), ('I', (e.b for e in edges)), ('f', (e.length for e in edges)),
                         ('H', (e.attr for e in edges)), ('I', (e.name for e in edges)),
                         ('I', (e.way_id for e in edges)), ('I', offsets), ('H', counts)):
        out += array.array(code, values).tobytes()
        _pad(out)
    out += points
    _pad(out)
    for from_edge, via, to_edge, only in tile.restrictions:
        out += struct.pack('<IIIB3x', from_edge, via, to_edge, 1 if only else 0)
    return bytes(out)
