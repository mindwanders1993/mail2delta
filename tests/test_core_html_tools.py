"""Unit tests for msgraph_email_core.html_tools."""

from msgraph_email_core.html_tools import HTMLTableExtractor


def test_get_plain_text():
    html = "<div><p>Hello <b>World</b>!</p><br/><a href='http://example.com'>Link</a></div>"
    text = HTMLTableExtractor.get_plain_text(html)
    assert "Hello" in text
    assert "World" in text
    assert "Link" in text
    assert "<p>" not in text


def test_extract_all_tables_simple():
    html = """
    <html>
        <body>
            <p>Intro text</p>
            <table border="1">
                <tr><th>Col1</th><th>Col2</th></tr>
                <tr><td>Val1</td><td>Val2</td></tr>
                <tr><td>Val3</td><td>Val4</td></tr>
            </table>
        </body>
    </html>
    """
    tables = HTMLTableExtractor.extract_all_tables(html)
    assert len(tables) == 1
    df = tables[0]
    assert df.shape[0] == 2  # 2 data rows under <th> headers
    assert list(df.columns) == ["Col1", "Col2"]


def test_extract_multiple_tables():
    html = """
    <div>
        <table id="tbl1">
            <tr><td>Header A</td><td>Header B</td></tr>
            <tr><td>100</td><td>200</td></tr>
        </table>
        <p>Divider</p>
        <table id="tbl2">
            <tr><td>Header X</td><td>Header Y</td></tr>
            <tr><td>300</td><td>400</td></tr>
        </table>
    </div>
    """
    tables = HTMLTableExtractor.extract_all_tables(html)
    assert len(tables) == 2
    assert tables[0].iloc[1, 0] == 100 or str(tables[0].iloc[1, 0]) == "100"
    assert tables[1].iloc[1, 0] == 300 or str(tables[1].iloc[1, 0]) == "300"


def test_extract_table_by_header_keyword():
    html = """
    <table>
        <tr><td>請求先コード</td><td>7910890000</td></tr>
        <tr><td>支払額</td><td>¥1,234,567</td></tr>
    </table>
    """
    tbl = HTMLTableExtractor.extract_table_by_header_keyword(html, "請求先コード")
    assert tbl is not None
    assert "請求先コード" in tbl.to_string()
