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


def test_google_doc_code_blocks():
    """
    Ensure that Code Building Blocks are correctly disentangled.
    """
    input = """
<p class="c3"><span>&#60419;</span><span class="c6">&nbsp; &nbsp; </span><span class="c17 c6">def</span><span
            class="c6">&nbsp;</span><span class="c0">identify_code_blocks(self,</span><span
            class="c6">&nbsp;</span><span class="c0">soup:</span><span class="c6">&nbsp;</span><span
            class="c0 c21">BeautifulSoup):</span></p>
    <p class="c3"><span class="c0">&nbsp; &nbsp; &nbsp; &nbsp; </span><span class="c6 c23">&quot;&quot;&quot; There&#39;s an empty
            line below on purpose. &quot;&quot;&quot;<br></span></p>
    <p class="c3"><span class="c6">&nbsp; &nbsp; &nbsp; &nbsp; </span><span class="c17 c6">for</span><span
            class="c6">&nbsp;</span><span class="c0">pre</span><span class="c6">&nbsp;</span><span
            class="c17 c6">in</span><span class="c6">&nbsp;</span><span class="c0">soup.find_all(</span><span
            class="c9 c6">&quot;pre&quot;</span><span class="c0">):</span></p>
    <p class="c3"><span class="c6">&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; </span><span class="c0">code</span><span
            class="c6">&nbsp;</span><span class="c0">=</span><span class="c6">&nbsp;</span><span
            class="c6 c9">&quot;&quot;</span><span class="c0">.join(pre.contents)</span></p>
    <p class="c3"><span class="c6">&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; </span><span class="c17 c6">if</span><span
            class="c6">&nbsp;</span><span class="c9 c6">&quot;import &quot;</span><span class="c6">&nbsp;</span><span
            class="c17 c6">in</span><span class="c6">&nbsp;</span><span class="c0">code</span><span
            class="c6">&nbsp;</span><span class="c0">or</span><span class="c6">&nbsp;</span><span
            class="c9 c6">&quot;def &quot;</span><span class="c6">&nbsp;</span><span class="c17 c6">in</span><span
            class="c6">&nbsp;</span><span class="c0">code:</span></p>
    <p class="c3"><span class="c6">&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; </span><span
            class="c0">pre[</span><span class="c9 c6">&quot;class&quot;</span><span class="c0">]</span><span
            class="c6">&nbsp;</span><span class="c0">=</span><span class="c6">&nbsp;</span><span
            class="c9 c6">&quot;python&quot;</span></p>
    <p class="c3 c12"><span class="c5"></span></p>
    <p class="c3"><span class="c1">&#60418;</span></p>
"""
    from doctomd import HTMLCleaner

    cleaner = HTMLCleaner()
    soup = BeautifulSoup(input, "lxml")

    cleaner.process_building_block_code(soup)

    assert soup.html.body.pre is not None
    assert (
        soup.html.body.pre.string
        == '''    def identify_code_blocks(self, soup: BeautifulSoup):
        """ There's an empty line below on purpose. """

        for pre in soup.find_all("pre"):
            code = "".join(pre.contents)
            if "import " in code or "def " in code:
                pre["class"] = "python"
'''
    )


def test_google_code_blocks_with_adjacent_text():
    """
    There was a bug where if no blank line was left before and after a google code block then the results were messed up.
    """

    # Google Doc: para, code block, para
    input = """<body class="c3 doc-content">
    <p class="c0"><span class="c2">This is some text that is immediately followed by a code block, with no blank line.</span></p>
    <p class="c0"><span>&#60419;</span><span class="c4">import</span><span class="c8">&nbsp;</span><span
            class="c5">pytest</span></p>
    <p class="c0 c6"><span class="c1"></span></p>
    <p class="c0"><span class="c4">def </span><span class="c5 c9">test_contiguous_building_block():</span></p>
    <p class="c0"><span class="c5">&nbsp; &nbsp; </span><span class="c7">&quot;&quot;&quot; This has been written to fix
            a problem where code blocks are not correctly separated from the paragraphs immediately above and below.
            &quot;&quot;&quot;</span></p>
    <p class="c0"><span class="c5">&nbsp; &nbsp; </span><span class="c4">pass</span></p>
    <p class="c0"><span class="c2">&#60418;And this is the next paragraph, that should be normal text.</span></p>
    <p class="c0"><span class="c2">Yet another paragraph, that should be normal text.</span></p>

</body>"""

    from doctomd import HTMLCleaner

    cleaner = HTMLCleaner()
    soup = BeautifulSoup(input, "lxml")

    cleaner.process_building_block_code(soup)

    assert soup.html.body.pre is not None
    assert (
        soup.html.body.p.string.strip()
        == """
This is some text that is immediately followed by a code block, with no blank line.
""".strip()
    )

    print(str(soup))

    assert (
        soup.html.body.pre.string.strip()
        == '''
import pytest

def test_contiguous_building_block():
    """ This has been written to fix a problem where code blocks are not correctly separated from the paragraphs immediately above and below. """
    pass
'''.strip()
    )
    next_p = soup.html.body.pre.find_next_sibling("p")
    assert next_p is not None
    assert (
        next_p.span.string
        == "And this is the next paragraph, that should be normal text."
    )


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
