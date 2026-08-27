"""
tests.test_core_parser
~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for Core Utilities: CurrencyCleaner and HTMLParser.
"""

from core.currency_cleaner import CurrencyCleaner
from core.html_parser import HTMLParser


def test_currency_cleaner_global_formats():
    # US / UK
    assert CurrencyCleaner.clean("$1,500.50") == 1500.50
    assert CurrencyCleaner.clean("($250.00)") == -250.00
    assert CurrencyCleaner.clean("£10,000.00") == 10000.00
    assert CurrencyCleaner.clean("-£500.00") == -500.00

    # Euro & Asian Currencies
    assert CurrencyCleaner.clean("€2,345.67") == 2345.67
    assert CurrencyCleaner.clean("¥180,123,447") == 180123447.0
    assert CurrencyCleaner.clean("￥1,500,000") == 1500000.0
    assert CurrencyCleaner.clean("¥-25,226,790") == -25226790.0
    assert CurrencyCleaner.clean("△500,000") == -500000.0
    assert CurrencyCleaner.clean("▲1,234,567") == -1234567.0
    assert CurrencyCleaner.clean("150,000円") == 150000.0

    # Edge cases
    assert CurrencyCleaner.clean("0") == 0.0
    assert CurrencyCleaner.clean("-") is None
    assert CurrencyCleaner.clean("N/A") is None
    assert CurrencyCleaner.clean("#DIV/0!") is None
    assert CurrencyCleaner.clean(None) is None


def test_html_parser_to_text():
    html = "<p>Hello World<br>Second Line</p><table><tr><td>Cell 1</td><td>Cell 2</td></tr></table>"
    text = HTMLParser.html_to_text(html)
    assert "Hello World" in text
    assert "Second Line" in text
    assert "Cell 1" in text
    assert "Cell 2" in text


def test_html_parser_extract_tables():
    html = """
    <table>
        <tr><th>Col A</th><th>Col B</th></tr>
        <tr><td>Val 1</td><td>Val 2</td></tr>
    </table>
    """
    tables = HTMLParser.extract_tables(html)
    assert len(tables) == 1
    df = tables[0]
    assert df.shape == (2, 2)
    assert df.iloc[0, 0] == "Col A"
    assert df.iloc[1, 1] == "Val 2"
