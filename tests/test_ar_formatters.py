"""Unit tests for ar_collections_pipeline.formatters."""

from datetime import date

from ar_collections_pipeline.formatters import JapaneseCurrencyCleaner


def test_clean_standard_yen():
    assert JapaneseCurrencyCleaner.clean("¥1,234,567") == 1234567.0
    assert JapaneseCurrencyCleaner.clean("￥144,590,047") == 144590047.0


def test_clean_backslash_variant():
    assert JapaneseCurrencyCleaner.clean(r"\397,375,664") == 397375664.0


def test_clean_triangle_negative():
    assert JapaneseCurrencyCleaner.clean("△25,226,790") == -25226790.0
    assert JapaneseCurrencyCleaner.clean("▲1,000") == -1000.0


def test_clean_minus_signs():
    assert JapaneseCurrencyCleaner.clean("¥-25,226,790") == -25226790.0
    assert JapaneseCurrencyCleaner.clean("-¥500") == -500.0
    assert JapaneseCurrencyCleaner.clean("(1,234)") == -1234.0


def test_clean_zero_and_special():
    assert JapaneseCurrencyCleaner.clean("¥0") == 0.0
    assert JapaneseCurrencyCleaner.clean("0") == 0.0
    assert JapaneseCurrencyCleaner.clean("1,234円") == 1234.0


def test_clean_errors_and_blanks():
    assert JapaneseCurrencyCleaner.clean("#DIV/0!") is None
    assert JapaneseCurrencyCleaner.clean("#N/A") is None
    assert JapaneseCurrencyCleaner.clean("-") is None
    assert JapaneseCurrencyCleaner.clean("") is None
    assert JapaneseCurrencyCleaner.clean(None) is None


def test_extract_date_from_label():
    assert JapaneseCurrencyCleaner.extract_date_from_label("3/23 支払額", default_year=2026) == date(2026, 3, 23)
    assert JapaneseCurrencyCleaner.extract_date_from_label("3/10払", default_year=2026) == date(2026, 3, 10)
    assert JapaneseCurrencyCleaner.extract_date_from_label("2026/03/31 振込分") == date(2026, 3, 31)
    assert JapaneseCurrencyCleaner.extract_date_from_label("2026年3月15日") == date(2026, 3, 15)
