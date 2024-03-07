from bs4 import BeautifulSoup


def test_fix_backticks():
    """
    Ensure fix_backticks doesn't remove intermediate tags.
    """
    from doctomd import fix_backticks

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

    fix_backticks(soup)

    assert soup.html.body.p is not None
    assert soup.html.body.p.a is not None
    assert (
        soup.html.body.p.a["href"]
        == "https://huggingface.co/datasets/MongoDB/cosmopedia-wikihow-chunked"
    )
    assert soup.html.body.p.a.code is not None
    assert soup.html.body.p.a.code.string == "cosmopedia-wikihow-chunked"
