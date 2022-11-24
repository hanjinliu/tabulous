from tabulous._psygnal import SignalArray
from unittest.mock import MagicMock

class A:
    sig = SignalArray(int)

def test_partial_connect():
    mock = MagicMock()
    a = A()
    a.sig[2:6, 0:4].connect(mock)

    mock.assert_not_called()

    a.sig[4, 3].emit(1)
    mock.assert_called_with(1)

    a.sig[5:8, 3:9].emit(2)
    mock.assert_called_with(2)

    mock.reset_mock()

    a.sig[7:12, 0:10].emit(2)
    mock.assert_not_called()

def test_total_connect():
    mock = MagicMock()
    a = A()
    a.sig.connect(mock)

    mock.assert_not_called()

    a.sig[4, 3].emit(1)
    mock.assert_called_with(1)

    a.sig[5:8, 3:9].emit(2)
    mock.assert_called_with(2)

    a.sig[7:12, 0:10].emit(3)
    mock.assert_called_with(3)

def test_disconnect():
    mock = MagicMock()
    a = A()
    a.sig.connect(mock)
    assert mock in a.sig

    a.sig.disconnect(mock)
    assert mock not in a.sig

    mock.assert_not_called()
    a.sig.emit(0)
    mock.assert_not_called()

def test_disconnect_method():
    mock = MagicMock()

    class X:
        def f(self, x):
            mock(x)

    a = A()
    x = X()
    a.sig.connect(x.f)
    assert x.f in a.sig

    a.sig.disconnect(x.f)
    assert x.f not in a.sig

    mock.assert_not_called()
    a.sig.emit(0)
    mock.assert_not_called()


def test_blocked():
    mock = MagicMock()
    a = A()
    a.sig.connect(mock)

    with a.sig.blocked():
        a.sig.emit(0)

    mock.assert_not_called()
