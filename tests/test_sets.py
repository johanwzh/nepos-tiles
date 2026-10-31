"""Routing for all modes (2026-11-01): one network per set, read in one pass."""
from pathlib import Path

import pytest

from build.derive import FERRY_CLASS, TRACK_CLASS, set_of_way, track_direction
from build.read import read, read_sets

SMALL = str(Path(__file__).parent / 'fixtures' / 'small.osm')


@pytest.fixture(scope='module')
def nets():
    return read_sets(SMALL)


def ids(net):
    return sorted(w[0] for w in net.ways)


def way(net, way_id):
    return next((w for w in net.ways if w[0] == way_id), None)


def test_set_of_way():
    assert set_of_way({'railway': 'light_rail'}) == {'tram', 'metro'}
    assert set_of_way({'railway': 'rail'}) == {'rail'}
    assert set_of_way({'railway': 'narrow_gauge'}) == {'rail'}
    assert set_of_way({'railway': 'subway'}) == {'metro'}
    assert set_of_way({'railway': 'tram'}) == {'tram'}
    assert set_of_way({'aerialway': 'gondola'}) == {'cable'}
    assert set_of_way({'aerialway': 'chair_lift'}) == {'cable'}
    assert set_of_way({'railway': 'funicular'}) == {'cable'}
    assert set_of_way({'aerialway': 'goods'}) == set()
    assert set_of_way({'aerialway': 'zip_line'}) == set()
    assert set_of_way({'route': 'ferry'}) == {'ferry'}
    assert set_of_way({'highway': 'primary'}) == set()
    assert set_of_way({'railway': 'disused', 'disused:railway': 'rail'}) == set()
    assert set_of_way({'railway': 'rail', 'abandoned': 'yes'}) == set()


def test_track_direction():
    assert track_direction({}) == 0
    assert track_direction({'oneway': 'yes'}) == 1
    assert track_direction({'oneway': '-1'}) == 2


def test_read_sets_tracks(nets):
    assert ids(nets['rail']) == [500]
    assert way(nets['rail'], 500)[1] == (TRACK_CLASS, 0, 130, 0, 0, 0, 0)
    assert way(nets['rail'], 500)[2] == 'Gjøvikbanen'
    assert ids(nets['tram']) == [501, 502, 509]
    assert way(nets['tram'], 502)[1][1] == 1
    assert ids(nets['metro']) == [501, 503]
    assert ids(nets['cable']) == [505, 507]
    assert all(nets[s].restrictions == [] for s in ('rail', 'tram', 'metro', 'cable', 'ferry'))


def test_ferry_set_takes_every_ferry_and_relation_members(nets):
    assert ids(nets['ferry']) == [200, 201, 508]
    assert all(w[1][0] == FERRY_CLASS for w in nets['ferry'].ways)


def test_road_unchanged(nets):
    assert read(SMALL).ways == nets['road'].ways
    assert read(SMALL).restrictions == nets['road'].restrictions


def test_only_the_sets_asked_for():
    assert sorted(read_sets(SMALL, ('rail', 'ferry'))) == ['ferry', 'rail']


def test_level_crossings_of_tracks(nets):
    """A node tagged railway=railway_crossing: tracks cross there without a link (final review 2026-11-01)."""
    assert 45 in nets['tram'].crossings
    assert nets['road'].crossings == frozenset()
