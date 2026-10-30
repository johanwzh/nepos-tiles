from pathlib import Path

import pytest

from build.derive import FERRY_CLASS
from build.read import read

SMALL = str(Path(__file__).parent / 'fixtures' / 'small.osm')


@pytest.fixture(scope='module')
def net():
    return read(SMALL)


def way(net, way_id):
    return next((w for w in net.ways if w[0] == way_id), None)


def test_reads_bus_ways_only(net):
    assert sorted(w[0] for w in net.ways) == [100, 101, 102, 103, 200]
    assert net.stats['skip_no_bus'] == 1
    assert net.stats['road'] == 4


def test_way_values(net):
    way_id, attr, name, ids, lons, lats = way(net, 101)
    assert attr == (1, 1, 60, 0, 0, 0, 0)
    assert name == 'Rv 4'
    assert list(ids) == [11, 12, 13]
    assert list(lons) == [100_000_000, 100_100_000, 100_200_000]
    assert list(lats) == [599_100_000] * 3


def test_ferry_is_a_car_ferry_through_its_relation(net):
    ferry = way(net, 200)
    assert ferry is not None
    assert ferry[1][0] == FERRY_CLASS
    assert net.stats['ferry'] == 1


def test_plain_ferry_is_not_a_road(net):
    assert way(net, 201) is None
    assert net.stats['skip_ferry_no_cars'] == 1


def test_restrictions_for_buses(net):
    assert sorted(net.restrictions) == [(100, 2, 100, True), (101, 12, 102, False)]
    assert net.stats['restrictions'] == 2
    assert net.stats['restrictions_not_bus'] == 1
    assert net.stats['restrictions_skipped_via_way'] == 1


def test_data_date_empty_without_header(net):
    assert net.data_date == ''
