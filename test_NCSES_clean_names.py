import pytest

from NCSES_clean_names import clean_date_part


@pytest.mark.parametrize(
    "raw, clean",
    [
        ("12", "12"),
        ("012", "12"),
        (" 12", "12"),
        (" 1 ", "1"),
        ("010 ", "10"),
        ("\t010 ", "10"),
    ],
)
def test_valid_clean_months(raw, clean):
    assert clean_date_part(raw, 1, 12) == clean


@pytest.mark.parametrize("raw", ("0", "", None, "13", "a13", "94", "z", "!"))
def test_invalid_clean_months(raw):
    assert clean_date_part(raw, 1, 12) == ""

