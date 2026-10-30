"""Derive the few values Nepos needs from OSM tags, one value per edge (proposal §3.3)."""
import re

ROAD_CLASSES = {
    'motorway': 0, 'motorway_link': 0, 'trunk': 0, 'trunk_link': 0,
    'primary': 1, 'primary_link': 1, 'secondary': 1, 'secondary_link': 1,
    'tertiary': 2, 'tertiary_link': 2, 'unclassified': 2, 'residential': 2, 'living_street': 2, 'road': 2,
    'busway': 2, 'bus_guideway': 2,
    'service': 3,
}
FERRY_CLASS = 4
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
    """key:physical preferred; metres or tonnes; 0 when missing or unparseable."""
    v, _ = _number(tags.get(key + ':physical') or tags.get(key))
    return v


def label(tags):
    return ' / '.join(x for x in (tags.get('ref'), tags.get('name')) if x)
