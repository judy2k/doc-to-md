#!/usr/bin/env python3

"""
A small command-line utility for converting Google Docs documents to Markdown that's suitable for pasting into ContentStack.
"""

from argparse import ArgumentParser
import logging
from logging import debug, info, warn
from pathlib import Path
import re
from subprocess import Popen, PIPE
import sys
from typing import List
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup
from cssutils import CSSParser
import mdformat


CSS_PARSER = CSSParser()


def is_code_font(f: str):
    return f.strip().strip("'\"").lower() in {
        "fira mono",
        "roboto mono",
        "source code pro",
        "courier new",
    }


def extract_code_styles(soup: BeautifulSoup) -> List[str]:
    result = set()
    for st in soup.find_all("style"):
        sheet = CSS_PARSER.parseString(st.string)
        for rule in sheet.cssRules.rulesOfType(1):
            # See if it contains a font-family rule:
            for s in rule.style.getProperties(name="font-family"):
                if is_code_font(s.value):
                    result.add(rule.selectorText.strip().strip("."))
    debug(f"Code classes in HTML: {', '.join(result)}")
    return result


def extract_span_styles(soup: BeautifulSoup):
    result = {}
    for st in soup.find_all("style"):
        sheet = CSS_PARSER.parseString(st.string)
        for rule in sheet.cssRules.rulesOfType(1):
            for s in rule.style.getProperties(name="font-weight"):
                if int(s.value) > 400:
                    result.setdefault("b", []).append(
                        rule.selectorText.strip().strip(".")
                    )
            for s in rule.style.getProperties(name="font-style"):
                if s.value == "italic":
                    result.setdefault("i", []).append(
                        rule.selectorText.strip().strip(".")
                    )
    debug(f"Span style classes: {', '.join(result)}")
    return result


def replace_style_spans(soup: BeautifulSoup):
    span_styles = extract_span_styles(soup)
    for new_tag, span_styles in span_styles.items():
        for span in soup.find_all("span", class_=span_styles):
            span.name = new_tag


def mark_code_blocks(soup: BeautifulSoup):
    code_styles = extract_code_styles(soup)
    for span in soup.find_all("span", class_=code_styles):
        p = span.parent
        if p.name in {"p", "div"}:
            if len(p.contents) == 1:  # Is it a line from a code BLOCK
                prev = p.previous_sibling
                text = str(p.string if p.string else "")
                if prev is None or prev.name != "pre":
                    # Hoist the '.string' content up to this level (remove 'span') and make it a 'pre'
                    p.name = "pre"
                    p.string = text
                else:
                    # prev is a 'pre' element - append the current '.string' to it (maybe with line break.)
                    prev.extend(["\r\n", text])
                    # Delete p
                    p.decompose()
            else:
                span.name = "code"


def fix_google_links(soup: BeautifulSoup):
    for link in soup.find_all(
        "a", attrs={"href": re.compile(r"https:\/\/www.google.com\/url")}
    ):
        link["href"] = parse_qs(urlparse(link["href"]).query)["q"][0]


def remove_ids(soup: BeautifulSoup):
    for tag in soup.find_all(id=True):
        del tag["id"]


def remove_classes(soup: BeautifulSoup):
    for tag in soup.find_all(class_=True):
        del tag["class"]


def remove_styles(soup: BeautifulSoup):
    for tag in soup.find_all(style=True):
        del tag["style"]


def identify_code_blocks(soup: BeautifulSoup):
    for pre in soup.find_all("pre"):
        code = "".join(pre.contents)
        if "import " in code or "def " in code:
            pre["class"] = "python"


def fix_backticks(soup: BeautifulSoup):
    soup.smooth()  # Relies on adjacent strings being concatenated.
    for tag in soup.find_all(True, string=re.compile(r"`")):
        new_contents = (
            BeautifulSoup(re.sub(r"`(.*?)`", r"<code>\1</code>", tag.string), "lxml")
            .html.body.p.extract()
            .contents
        )
        tag.clear()
        tag.extend(new_contents)


def remove_empty_paras(soup: BeautifulSoup):
    for tag in soup.find_all("span"):
        tag.unwrap()

    for tag in soup.find_all(lambda tag: tag.name == "p" and not tag.contents):
        tag.unwrap()


def main(argv=sys.argv[1:]):
    ap = ArgumentParser(prog="doc2md", description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument(
        "--no-pandoc",
        action="store_true",
        help="Output will be cleaned HTML instead of Markdown. This option is primarily for debugging.",
    )
    ap.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase the amount of output describing the operation of doc2md. This flag can be repeated to increase verbosity even more.",
    )
    ap.add_argument(
        "--no-format",
        action="store_true",
        help="Output will not be reformatted with mdformat. If --no-pandoc is supplied, then this option does nothing.",
    )

    args = ap.parse_args(argv)

    log_level = {0: logging.WARN, 1: logging.INFO}.get(args.verbose, logging.DEBUG)

    logging.basicConfig(format="%(levelname)s: %(message)s", level=log_level)
    logging.getLogger("markdown_it").setLevel(logging.WARN)

    path: Path = args.input
    output_path: Path = args.output

    soup = BeautifulSoup(path.read_text(), "lxml")
    mark_code_blocks(soup)
    replace_style_spans(soup)
    fix_google_links(soup)
    remove_ids(soup)
    remove_classes(soup)
    remove_styles(soup)
    identify_code_blocks(soup)
    fix_backticks(soup)
    remove_empty_paras(soup)

    if args.no_pandoc:
        info("No pandoc")
        output_path.write_text(str(soup))
    else:
        pandoc = Popen(
            [
                "pandoc",
                "--to",
                "gfm-raw_html+pipe_tables",
                "-f",
                "html-native_divs-native_spans-raw_html",
                "-o",
                str(output_path),
            ],
            stdin=PIPE,
            text=True,
        )

        pandoc.communicate(input=str(soup))
        pandoc.wait()

        if not args.no_format:
            mdformat.file(
                output_path,
                options={
                    "wrap": "no",
                },
                extensions={"gfm"},
            )


if __name__ == "__main__":
    main()
