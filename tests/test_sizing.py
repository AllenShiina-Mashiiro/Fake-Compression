import pytest
from fake_compression.sizing import GIB, plan_volumes

@pytest.mark.parametrize(("size", "expected"), [
    (0, None), (GIB, None), (GIB + 1, 2 * GIB),
    (5 * GIB, 2 * GIB), (5 * GIB + 1, 3 * GIB),
])
def test_volume_policy(size, expected):
    assert plan_volumes(size).volume_bytes == expected

def test_negative_size_rejected():
    with pytest.raises(ValueError):
        plan_volumes(-1)
