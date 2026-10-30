import array

from build.read import Network, Q


def way(way_id, coords, node_ids=None, attr=(2, 0, 0, 0, 0, 0, 0), name=''):
    """A Network way from [(lon, lat)] in degrees; node ids default to way_id * 100 + i."""
    ids = node_ids or [way_id * 100 + i for i in range(len(coords))]
    return (way_id, attr, name, array.array('q', ids),
            array.array('i', [round(x * Q) for x, _ in coords]), array.array('i', [round(y * Q) for _, y in coords]))


def network(ways, restrictions=()):
    return Network(list(ways), list(restrictions), {}, '')
