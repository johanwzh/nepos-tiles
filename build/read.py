"""Read an OSM extract: the ways a bus may use, car ferries and bus turn restrictions."""
import array
from collections import defaultdict
from typing import NamedTuple

import osmium

from build.derive import FERRY_CLASS, ROAD_CLASSES, YES, bus_allowed, direction, label, limit, speed_kmh

Q = 10_000_000                     # coordinates as integers, 1e-7 degree
CAR_KEYS = ('motor_vehicle', 'motorcar', 'hgv', 'bus')


class Network(NamedTuple):
    ways: list            # (way_id, attr, name, node_ids array('q'), lons array('i'), lats array('i'))
    restrictions: list    # (from_way, via_node, to_way, only)
    stats: dict
    data_date: str


def _relations(path, stats):
    """Pass 1: way ids of car-ferry routes, and turn restrictions that apply to a bus."""
    car_ferry_ways, restrictions = set(), []
    fp = osmium.FileProcessor(path).with_filter(osmium.filter.EntityFilter(osmium.osm.RELATION))
    for r in fp:
        t = r.tags
        kind = t.get('type')
        if kind == 'route' and t.get('route') == 'ferry':
            if any(t.get(k) in YES for k in CAR_KEYS):
                car_ferry_ways.update(m.ref for m in r.members if m.type == 'w')
        elif kind == 'restriction':
            value = t.get('restriction:bus') or t.get('restriction') or ''
            if not value.startswith(('no_', 'only_')):
                continue
            excepted = {x.strip() for x in t.get('except', '').split(';')}
            if t.get('restriction:bus') is None and excepted & {'psv', 'bus'}:
                stats['restrictions_not_bus'] += 1
                continue
            roles = defaultdict(list)
            for m in r.members:
                roles[m.role].append((m.type, m.ref))
            if [x[0] for x in roles['via']] != ['n']:
                stats['restrictions_skipped_via_way'] += 1
                continue
            if len(roles['from']) != 1 or len(roles['to']) != 1 or roles['from'][0][0] != 'w' or roles['to'][0][0] != 'w':
                stats['restrictions_skipped_other'] += 1
                continue
            restrictions.append((roles['from'][0][1], roles['via'][0][1], roles['to'][0][1], value.startswith('only_')))
            stats['restrictions'] += 1
    return car_ferry_ways, restrictions


def _data_date(path):
    reader = osmium.io.Reader(path, osmium.osm.osm_entity_bits.NOTHING)
    try:
        return reader.header().get('osmosis_replication_timestamp', '')
    finally:
        reader.close()


def read(path: str) -> Network:
    stats = defaultdict(int)
    car_ferry_ways, restrictions = _relations(path, stats)
    ways = []
    fp = osmium.FileProcessor(path).with_locations().with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
    for w in fp:
        t = w.tags
        hw = t.get('highway')
        ferry = t.get('route') == 'ferry'
        if not ferry and (hw not in ROAD_CLASSES or t.get('area') == 'yes'):
            continue
        tags = {k: v for k, v in t}
        if ferry and w.id in car_ferry_ways and not any(tags.get(k) in YES for k in CAR_KEYS):
            tags['motor_vehicle'] = 'yes'
        if not bus_allowed(tags, ferry):
            stats['skip_ferry_no_cars' if ferry else 'skip_no_bus'] += 1
            continue
        ids, lons, lats = array.array('q'), array.array('i'), array.array('i')
        try:
            for n in w.nodes:
                ids.append(n.ref)
                lons.append(round(n.lon * Q))
                lats.append(round(n.lat * Q))
        except osmium.InvalidLocationError:
            stats['skip_no_location'] += 1
            continue
        if len(ids) < 2:
            continue
        attr = (FERRY_CLASS if ferry else ROAD_CLASSES[hw], direction(tags, hw), speed_kmh(tags),
                limit(tags, 'maxheight'), limit(tags, 'maxwidth'), limit(tags, 'maxlength'), limit(tags, 'maxweight'))
        ways.append((w.id, attr, label(tags), ids, lons, lats))
        stats['ferry' if ferry else 'road'] += 1
    return Network(ways, restrictions, dict(stats), _data_date(path))
