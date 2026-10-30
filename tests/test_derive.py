from build.derive import ROAD_CLASSES, bus_allowed, direction, label, limit, speed_kmh


def test_road_classes():
    assert ROAD_CLASSES['motorway_link'] == 0
    assert ROAD_CLASSES['secondary'] == 1
    assert ROAD_CLASSES['busway'] == 2
    assert ROAD_CLASSES['service'] == 3
    assert 'footway' not in ROAD_CLASSES


def test_only_an_explicit_no_keeps_a_bus_off():
    assert bus_allowed({'access': 'private'}, False)
    assert bus_allowed({'access': 'no', 'psv': 'yes'}, False)
    assert not bus_allowed({'motor_vehicle': 'no'}, False)
    assert not bus_allowed({'bus': 'no', 'access': 'yes'}, False)


def test_ferry_needs_cars():
    assert not bus_allowed({}, True)
    assert bus_allowed({'motor_vehicle': 'yes'}, True)
    assert not bus_allowed({'motorcar': 'yes', 'hgv': 'no'}, True)


def test_direction_as_a_bus_sees_it():
    assert direction({'oneway': 'yes'}, 'primary') == 1
    assert direction({'oneway': '-1'}, 'primary') == 2
    assert direction({'oneway': 'yes', 'oneway:bus': 'no'}, 'primary') == 0
    assert direction({}, 'motorway') == 1
    assert direction({'junction': 'roundabout'}, 'tertiary') == 1
    assert direction({'oneway': 'reversible'}, 'primary') == 0


def test_speed():
    assert speed_kmh({'maxspeed': '80', 'maxspeed:hgv': '60'}) == 60
    assert speed_kmh({'maxspeed': '30 mph'}) == 48
    assert speed_kmh({'maxspeed': 'NO:urban'}) == 0
    assert speed_kmh({}) == 0


def test_limits():
    assert limit({'maxheight': '3.2', 'maxheight:physical': '3.4'}, 'maxheight') == 3.4
    assert limit({'maxweight': '3.5 t'}, 'maxweight') == 3.5
    assert limit({'maxheight': 'default'}, 'maxheight') == 0
    assert limit({'maxwidth': '2,5 m'}, 'maxwidth') == 2.5
    assert limit({}, 'maxlength') == 0


def test_label():
    assert label({'ref': 'E 6', 'name': 'Adolf Hedins vei'}) == 'E 6 / Adolf Hedins vei'
    assert label({'name': 'Storgata'}) == 'Storgata'
    assert label({}) == ''
