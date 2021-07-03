from numpy.testing import assert_equal, assert_allclose


def assert_equal_nounits(a, b):
    if hasattr(a, "value"):
        a = a.value
    if hasattr(b, "value"):
        b = b.value
    assert_equal(a, b)


def assert_allclose_nounits(a, b, rtol=1e-07, atol=0, 
                            equal_nan=True, err_msg='', 
                            verbose=True):
    if hasattr(a, "value"):
        a = a.value
    if hasattr(b, "value"):
        b = b.value
    assert_allclose(a, b, rtol=rtol, atol=atol,
                    equal_nan=equal_nan, err_msg=err_msg,
                    verbose=verbose)
