from numpy.testing import assert_equal


def assert_equal_nounits(a, b):
    if hasattr(a, "value"):
        a = a.value
    if hasattr(b, "value"):
        b = b.value
    assert_equal(a, b)