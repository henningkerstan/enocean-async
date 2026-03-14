from enocean_async.address import Address, BroadcastAddress


def test_conversion():
    for i in range(0, 4294967295, 100000):
        assert int(Address(i)) == i
        assert int(Address(str(Address(i)))) == i


def test_known_values():
    assert str(Address(0)) == "00:00:00:00"


def test_is_eurid():
    assert Address(0).is_eurid()
    assert Address("FF:7F:FF:FF").is_eurid()
    assert Address("FF:80:00:00").is_eurid() == False
    assert BroadcastAddress().is_eurid() == False


def test_broadcast():
    assert str(BroadcastAddress()) == "FF:FF:FF:FF"
    assert BroadcastAddress().is_broadcast()
    assert BroadcastAddress().is_base_address() == False
