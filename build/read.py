"""Read an OSM extract: the ways a bus may use, car ferries and bus turn restrictions; and (2026-11-01) the rail,
tram, metro, ferry and cable networks, all in one pass over the ways."""
import array
from collections import defaultdict
from typing import NamedTuple

import osmium

from build.derive import (FERRY_CLASS, ROAD_CLASSES, SETS, TRACK_CLASS, YES, bus_allowed, direction, label, limit,
                          set_of_way, speed_kmh, track_direction)

Q = 10_000_000                     # coordinates as integers, 1e-7 degree
CAR_KEYS = ('motor_vehicle', 'motorcar', 'hgv', 'bus')


class Network(NamedTuple):
    ways: list            # (way_id, attr, name, node_ids array('q'), lons array('i'), lats array('i'))
    restrictions: list    # (from_way, via_node, to_way, only)
    stats: dict
    data_date: str
    crossings: frozenset = frozenset()   # track sets: nodes where tracks cross without a link (railway_crossing)


def _level_crossings(path):
    """Node ids tagged railway=railway_crossing: two tracks cross there, a train cannot turn from one to the other."""
    fp = osmium.FileProcessor(path).with_filter(osmium.filter.EntityFilter(osmium.osm.NODE)) \
        .with_filter(osmium.filter.TagFilter(('railway', 'railway_crossing')))
    return frozenset(n.id for n in fp)


def _relations(path, stats):
    """Pass 1: way ids of car-ferry routes and of every ferry route, and turn restrictions that apply to a bus."""
    car_ferry_ways, ferry_ways, restrictions = set(), set(), []
    fp = osmium.FileProcessor(path).with_filter(osmium.filter.EntityFilter(osmium.osm.RELATION))
    for r in fp:
        t = r.tags
        kind = t.get('type')
        if kind == 'route' and t.get('route') == 'ferry':
            ferry_ways.update(m.ref for m in r.members if m.type == 'w')
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
    return car_ferry_ways, ferry_ways, restrictions


def _data_date(path):
    reader = osmium.io.Reader(path, osmium.osm.osm_entity_bits.NOTHING)
    try:
        return reader.header().get('osmosis_replication_timestamp', '')
    finally:
        reader.close()


def read(path: str) -> Network:
    """The road network (as before 2026-11-01)."""
    return read_sets(path, ('road',))['road']


def read_sets(path: str, sets=SETS) -> dict:
    """Each requested set's network, from one pass over the ways. Turn restrictions are for road only."""
    stats = {name: defaultdict(int) for name in sets}
    car_ferry_ways, ferry_ways, restrictions = _relations(path, stats.get('road', defaultdict(int)))
    ways = {name: [] for name in sets}
    others = [name for name in sets if name != 'road']
    fp = osmium.FileProcessor(path).with_locations().with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
    for w in fp:
        t = w.tags
        hw = t.get('highway')
        ferry = t.get('route') == 'ferry'
        road = 'road' in ways and (ferry or (hw in ROAD_CLASSES and t.get('area') != 'yes'))
        tags = {k: v for k, v in t} if road or t.get('railway') or t.get('aerialway') or ferry or w.id in ferry_ways else None
        if tags is None:
            continue
        member = set_of_way(tags) | ({'ferry'} if w.id in ferry_ways else set())
        want = [name for name in others if name in member]
        if road:
            if ferry and w.id in car_ferry_ways and not any(tags.get(k) in YES for k in CAR_KEYS):
                tags['motor_vehicle'] = 'yes'
            if not bus_allowed(tags, ferry):
                stats['road']['skip_ferry_no_cars' if ferry else 'skip_no_bus'] += 1
                road = False
        if not road and not want:
            continue
        ids, lons, lats = array.array('q'), array.array('i'), array.array('i')
        try:
            for n in w.nodes:
                ids.append(n.ref)
                lons.append(round(n.lon * Q))
                lats.append(round(n.lat * Q))
        except osmium.InvalidLocationError:
            for name in (['road'] if road else []) + want:
                stats[name]['skip_no_location'] += 1
            continue
        if len(ids) < 2:
            continue
        name_ = label(tags)
        if road:
            attr = (FERRY_CLASS if ferry else ROAD_CLASSES[hw], direction(tags, hw), speed_kmh(tags),
                    limit(tags, 'maxheight'), limit(tags, 'maxwidth'), limit(tags, 'maxlength'), limit(tags, 'maxweight'))
            ways['road'].append((w.id, attr, name_, ids, lons, lats))
            stats['road']['ferry' if ferry else 'road'] += 1
        for name in want:
            attr = (FERRY_CLASS, 0, speed_kmh(tags), 0, 0, 0, 0) if name == 'ferry' else \
                (TRACK_CLASS, track_direction(tags), speed_kmh(tags), 0, 0, 0, 0)
            ways[name].append((w.id, attr, name_, ids, lons, lats))
            stats[name]['ways'] += 1
    date = _data_date(path)
    crossings = _level_crossings(path) if any(name in ('rail', 'tram', 'metro', 'cable') for name in sets) else frozenset()
    return {name: Network(ways[name], restrictions if name == 'road' else [], dict(stats[name]), date,
                          crossings if name in ('rail', 'tram', 'metro', 'cable') else frozenset()) for name in sets}
