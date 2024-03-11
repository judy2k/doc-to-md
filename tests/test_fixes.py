from pytest import fail, skip  # noqa

from bs4 import BeautifulSoup


def test_fix_backticks():
    """
    Ensure fix_backticks doesn't remove intermediate tags.
    """
    from doctomd import HTMLCleaner

    soup = BeautifulSoup(
        """
        <html>
        <body>
        <p>
            <span><a href="https://huggingface.co/datasets/MongoDB/cosmopedia-wikihow-chunked">`cosmopedia-wikihow-chunked`</a></span>
        </p>
        </body>
        </html>
        """,
        "lxml",
    )
    cleaner = HTMLCleaner()
    cleaner.fix_backticks(soup)

    assert soup.html.body.p is not None
    assert soup.html.body.p.a is not None
    assert (
        soup.html.body.p.a["href"]
        == "https://huggingface.co/datasets/MongoDB/cosmopedia-wikihow-chunked"
    )
    assert soup.html.body.p.a.code is not None
    assert soup.html.body.p.a.code.string == "cosmopedia-wikihow-chunked"


def test_keep_pre_blocks():
    """
    process_google_doc_html does not modify existing <pre> blocks.
    """

    from doctomd import process_google_doc_html

    input = '''
<html>
<body>
<pre>
def remove_single_cell_tables(soup: BeautifulSoup):
    """
    Identify single cell tables, and replace them with their cell's contents.
    """
    
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) == 1:
            cells = rows[0].find_all("td")
            if len(cells) == 1:
                cells[0].unwrap()
                rows[0].unwrap()
                table.unwrap()
</pre>
</body>
</html>
'''
    soup = BeautifulSoup(input, "lxml")
    process_google_doc_html(soup)
    assert (
        soup.html.body.pre.string
        == '''
def remove_single_cell_tables(soup: BeautifulSoup):
    """
    Identify single cell tables, and replace them with their cell's contents.
    """
    
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) == 1:
            cells = rows[0].find_all("td")
            if len(cells) == 1:
                cells[0].unwrap()
                rows[0].unwrap()
                table.unwrap()
'''
    )


def test_keep_code_spans():
    """
    process_google_doc_html does not modify existing code spans in paragraphs
    """

    from doctomd import process_google_doc_html

    input = """
    <p>This is a sentence with a valid but unexpected <code>program</code> snippet in the middle.</p>
    """
    soup = BeautifulSoup(input, "lxml")
    process_google_doc_html(soup)
    assert list(str(i) for i in soup.html.body.p.contents) == [
        "This is a sentence with a valid but unexpected ",
        "<code>program</code>",
        " snippet in the middle.",
    ]


def test_code_paragraphs_become_pre():
    """
    process_google_doc_html combines adjacent <code> spans.
    """

    from doctomd import process_google_doc_html

    input = """<p><code>def this_should_be_pre()</code></p>"""
    soup = BeautifulSoup(input, "lxml")
    process_google_doc_html(soup)
    assert soup.html.body.pre is not None
    assert soup.html.body.pre.string == "def this_should_be_pre()"


def test_merge_adjacent_code_spans():
    """
    process_google_doc_html combines adjacent <code> spans.
    """

    skip("Not implemented yet")

    from doctomd import process_google_doc_html

    """Ensure <pre> blocks are preserved as they should be."""

    input = """
<html>
<body>
<p>This is a sentence with two adjacent <code>program</code> <code>snippets</code> in the middle.</p>
</body>
</html>
"""
    soup = BeautifulSoup(input, "lxml")
    process_google_doc_html(soup)
