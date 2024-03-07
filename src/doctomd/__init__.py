#!/usr/bin/env python3

"""
A small command-line utility for converting Google Docs documents to Markdown that's suitable for pasting into ContentStack.
"""

from logging import debug
import re

from typing import List
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup, Tag
from cssutils import CSSParser


CSS_PARSER = CSSParser()


def is_code_font(f: str):
    """
    Determines if the font name provided as `f` is considered to be a code font.
    """
    return f.strip().strip("'\"").lower() in {
        "fira mono",
        "roboto mono",
        "source code pro",
        "courier new",
        "consolas",
    }


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


def extract_code_styles(soup: BeautifulSoup) -> List[str]:
    """
    Identify the styles in the stylesheet that specify fixed-width fonts,
    and create a list of these "code" classes.
    """
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
    """
    Some <span> tags are for marking what should be <b> or <i>.

    This function goes through all the defined classes, determining which should
    be considered "bold" or "italic" classes, and then returns a dict with the
    keys "b" and "i",
    with each value being a list of classes that match this classification.
    """
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
    """
    Locate all spans that should be replaced with <b> or <i> tags,
    and make the fix.
    """
    span_styles = extract_span_styles(soup)
    for new_tag, span_styles in span_styles.items():
        for span in soup.find_all("span", class_=span_styles):
            span.name = new_tag


def mark_code_blocks(soup: BeautifulSoup):
    """
    Attempts to find consecutive lines of code and concatenate them into a single
    code block contained within a <pre> tag.
    """
    # TODO: For this to work consistently, it needs to have a tag and modify approach.
    # Step 1: Identify all code tokens
    # Step 2: Consolidate consecutive code tokens
    # Step 3: Identify and resolve code blocks (<pre>) vs code spans (<code>).
    code_styles = extract_code_styles(soup)
    for span in soup.find_all("span", class_=code_styles):
        p = span.parent
        if p.name in {"p", "div", "td"}:
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
                # If the previous element is a <code>, append this, otherwise mark it as a <code> itself.
                prev = span.previous_sibling
                if prev is not None and prev.name == "code":
                    # Append to previous code block:
                    prev.extend(span.contents)
                    span.decompose()
                else:
                    span.name = "code"

    soup.smooth()
    # Sometimes the formatting results in a paragraph containing a single <code> tag.
    # Let's see what we can do.
    for code in soup.find_all("code"):
        # If there's a <br/> in the code span, then it should be a <pre>:
        if code.find_all("br"):
            for item in code.contents:
                if isinstance(item, Tag):
                    if item.name == "br":
                        item.replace_with("\n")

        p = code.parent
        if p.name in {"p", "div", "td"}:
            if len(p.contents) == 1:  # Is it a line from a code BLOCK
                code.unwrap()
                p.name = "pre"

    # for p in soup.find_all("p"):

    # for pre in soup.find_all("pre"):
    #     pre.smooth()


def fix_google_links(soup: BeautifulSoup):
    """
    Google does this horrible link redirection thing. Fix it.
    """
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
    """
    Replace backticks (`) in the content with <code> tags.
    """

    soup.smooth()  # Relies on adjacent strings being concatenated.

    # Loop through any tag with content that includes a backtick.
    for tag in soup.find_all(True, string=re.compile(r"`")):
        # Do a regex substitution to create the code tags.
        # Then re-parse with bs4, and insert the new content into the existing tag.
        # If there's a better way to re-create the tag soup from the substituted
        # string, I'd love to know it.

        # From the bs4 docs: If a tag’s only child is another tag, and that tag
        # has a .string, then the parent tag is considered to have the same
        # .string as its child.
        # ☝🏻 This is quite annoying behaviour.
        if not (len(tag.contents) == 1 and isinstance(tag.contents[0], Tag)):
            content_body = BeautifulSoup(
                re.sub(r"`(.*?)`", r"<code>\1</code>", tag.string), "lxml"
            ).html.body
            if content_body.p is not None:
                tag_to_extract = content_body.p
            else:
                tag_to_extract = content_body
            new_contents = tag_to_extract.extract().contents
            tag.clear()
            tag.extend(new_contents)


def remove_empty_paras(soup: BeautifulSoup):
    for tag in soup.find_all("span"):
        tag.unwrap()

    for tag in soup.find_all(lambda tag: tag.name == "p" and not tag.contents):
        tag.unwrap()
