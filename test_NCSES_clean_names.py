import pytest

from NCSES_clean_names import clean_integer


@pytest.mark.parametrize(
    "raw, clean",
    [
        ("1", "1"),
        ("10", "10"),
        ("12", "12"),
        ("012", "12"),
        (" 12", "12"),
        (" 1 ", "1"),
        ("010 ", "10"),
        ("\t010 ", "10"),
    ],
)
def test_valid_clean_months(raw, clean):
    assert clean_integer(raw, 1, 12) == clean


@pytest.mark.parametrize(
    "raw",
    (
        None,
        "",
        " ",
        "    ",
        r"\t",
        "\t",
        r"\b",
        "\b",
        "-1",
        "0",
        "13",
        "14",
        "65536",
        "a13",
        "z",
        "!",
        "??",
        "NULL",
        "N/A",
    ),
)
def test_invalid_clean_months(raw):
    assert clean_integer(raw, 1, 12) == ""
