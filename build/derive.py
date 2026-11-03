"""Derive the few values Nepos needs from OSM tags, one value per edge (proposal §3.3)."""
import re

ROAD_CLASSES = {
    'motorway': 0, 'motorway_link': 0, 'trunk': 0, 'trunk_link': 0,
    'primary': 1, 'primary_link': 1, 'secondary': 1, 'secondary_link': 1,
    # tertiary has a class of its own (2026-11-03): Nepos allows U-turns on minor roads, not on tertiary; Nepos 2.6.0
    # costs class 5 as a minor road
    'tertiary': 5, 'tertiary_link': 5, 'unclassified': 2, 'residential': 2, 'living_street': 2, 'road': 2,
    'busway': 2, 'bus_guideway': 2,
    'service': 3,
}
FERRY_CLASS = 4
TRACK_CLASS = 0                    # every edge of a rail, tram, metro or cable set
YES = {'yes', 'designated', 'permissive', 'destination', 'private', 'customers', 'delivery', 'official', 'permit'}
MPH = 1.609344


def bus_allowed(tags, ferry):
    """Most specific tag wins; only an explicit 'no' keeps a bus off. A ferry needs a sign that it carries cars:
    a vehicle tag, or ferry=<road class> (the road it carries, e.g. Kragerø - Skåtøyroa)."""
    if ferry:
        if any(tags.get(k) == 'no' for k in ('bus', 'hgv', 'motor_vehicle', 'motorcar')):
            return False
        return tags.get('ferry') in ROAD_CLASSES or any(tags.get(k) in YES for k in ('motor_vehicle', 'motorcar', 'hgv', 'bus'))
    for k in ('bus', 'psv', 'motor_vehicle', 'vehicle', 'access'):
        v = tags.get(k)
        if v == 'no':
            return False
        if v in YES:
            return True
    return True


def direction(tags, highway):
    """0 both, 1 forward, 2 backward — as a bus sees it. 'reversible' counts as both."""
    if any(tags.get(k) == 'no' for k in ('oneway:bus', 'oneway:psv')):
        return 0
    v = tags.get('oneway')
    if v in ('yes', '1', 'true'):
        return 1
    if v == '-1':
        return 2
    if v is None and (highway == 'motorway' or tags.get('junction') in ('roundabout', 'circular')):
        return 1
    return 0


_NUMBER = re.compile(r'^\s*(\d+(?:[.,]\d+)?)\s*(m|t|mph|km/h|kmh)?\s*$')


def _number(value):
    """(number, unit) or (0, None) when missing or not a plain number."""
    m = _NUMBER.match(value.lower()) if value else None
    if not m:
        return 0.0, None
    return float(m.group(1).replace(',', '.')), m.group(2)


def speed_kmh(tags):
    """Lower of maxspeed:hgv and maxspeed in km/h; 0 when neither is a number."""
    speeds = []
    for k in ('maxspeed:hgv', 'maxspeed'):
        v, unit = _number(tags.get(k))
        if unit == 'mph':
            v *= MPH
        if v > 0:
            speeds.append(round(v))
    return min(speeds) if speeds else 0


def limit(tags, key):
    """The lowest of key and key:physical (user 2026-11-03: whatever the tag, the lowest value is the limit); metres or
    tonnes; 0 when neither is a plain number."""
    values = [v for v in (_number(tags.get(k))[0] for k in (key, key + ':physical')) if v > 0]
    return min(values) if values else 0


def label(tags):
    return ' / '.join(x for x in (tags.get('ref'), tags.get('name')) if x)


# Routing for all modes (2026-11-01): the sets besides road, by the OSM tags a way needs. Light rail is in both tram
# and metro, because OSM uses it for both (Bybanen, parts of the T-bane).
SETS = ('road', 'rail', 'tram', 'metro', 'ferry', 'cable')
RAILWAY_SETS = {'rail': {'rail'}, 'narrow_gauge': {'rail'}, 'tram': {'tram'}, 'light_rail': {'tram', 'metro'},
                'subway': {'metro'}, 'funicular': {'cable'}}
# Aerialways that carry people; goods lifts, zip lines and pylons are not
AERIALWAYS = {'cable_car', 'gondola', 'mixed_lift', 'chair_lift', 'drag_lift', 't-bar', 'j-bar', 'platter',
              'rope_tow', 'magic_carpet'}
GONE = ('disused', 'abandoned', 'construction', 'proposed', 'razed', 'dismantled')


def set_of_way(tags):
    """The sets other than road a way belongs to (ferry by its own tag; relation members are added by the reader)."""
    if any(tags.get(k) == 'yes' for k in GONE):
        return set()
    if tags.get('route') == 'ferry':
        return {'ferry'}
    if tags.get('aerialway') in AERIALWAYS:
        return {'cable'}
    return set(RAILWAY_SETS.get(tags.get('railway'), ()))


def track_direction(tags):
    """0 both, 1 forward, 2 backward: a track is two-way unless it says oneway."""
    v = tags.get('oneway')
    if v in ('yes', '1', 'true'):
        return 1
    if v == '-1':
        return 2
    return 0
