#!/usr/bin/env python3

"""
A small command-line utility for converting Google Docs documents to Markdown
that's suitable for pasting into ContentStack.
"""

import logging
from logging import debug, info, getLogger
import re

from typing import List
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup, Tag
from cssutils import CSSParser


def flatten_html_line(line: Tag) -> str:
    for br in line.find_all("br"):
        br.replace_with("\n")
    line.smooth()
    result = re.sub(r"\n\s+", r" ", "".join(line.strings))
    return result


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


class HTMLCleaner:
    def __init__(self):
        css_parser_logger = getLogger("css_parser")
        css_parser_logger.setLevel(getLogger().level + 10)
        self.css_parser = CSSParser(log=css_parser_logger)

    def remove_single_cell_tables(self, soup: BeautifulSoup):
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

    def _extract_code_styles(self, soup: BeautifulSoup) -> List[str]:
        """
        Identify the styles in the stylesheet that specify fixed-width fonts,
        and create a list of these "code" classes.
        """

        result = set()
        for st in soup.find_all("style"):
            sheet = self.css_parser.parseString(st.string)
            for rule in sheet.cssRules.rulesOfType(1):
                # See if it contains a font-family rule:
                for s in rule.style.getProperties(name="font-family"):
                    if is_code_font(s.value):
                        result.add(rule.selectorText.strip().strip("."))
        debug(f"Code classes in HTML: {', '.join(result)}")
        return result

    def extract_span_styles(self, soup: BeautifulSoup):
        """
        Some <span> tags are for marking what should be <b> or <i>.

        This function goes through all the defined classes, determining which should
        be considered "bold" or "italic" classes, and then returns a dict with the
        keys "b" and "i",
        with each value being a list of classes that match this classification.
        """
        result = {}
        for st in soup.find_all("style"):
            sheet = self.css_parser.parseString(st.string)
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

    def replace_style_spans(self, soup: BeautifulSoup):
        """
        Locate all spans that should be replaced with <b> or <i> tags,
        and make the fix.
        """
        span_styles = self.extract_span_styles(soup)
        for new_tag, span_styles in span_styles.items():
            for span in soup.find_all("span", class_=span_styles):
                span.name = new_tag

    def mark_code_blocks(self, soup: BeautifulSoup):
        """
        Attempts to find consecutive lines of code and concatenate them into a single
        code block contained within a <pre> tag.
        """
        # TODO: For this to work consistently, it needs to have a tag and modify approach.
        # Step 1: Identify all code tokens
        # Step 2: Consolidate consecutive code tokens
        # Step 3: Identify and resolve code blocks (<pre>) vs code spans (<code>).
        code_styles = self._extract_code_styles(soup)
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

    def fix_google_links(self, soup: BeautifulSoup):
        """
        Google does this horrible link redirection thing. Fix it.
        """
        for link in soup.find_all(
            "a", attrs={"href": re.compile(r"https:\/\/www.google.com\/url")}
        ):
            link["href"] = parse_qs(urlparse(link["href"]).query)["q"][0]

    def remove_ids(self, soup: BeautifulSoup):
        for tag in soup.find_all(id=True):
            del tag["id"]

    def remove_classes(self, soup: BeautifulSoup):
        for tag in soup.find_all(class_=True):
            del tag["class"]

    def remove_styles(self, soup: BeautifulSoup):
        for tag in soup.find_all(style=True):
            del tag["style"]

    def identify_code_blocks(self, soup: BeautifulSoup):
        for pre in soup.find_all("pre"):
            code = "".join(pre.contents)
            if "import " in code or "def " in code:
                pre["class"] = "python"

    def process_building_block_code(self, soup: BeautifulSoup):
        """
        Replace Code Building Blocks that can be inserted into a Google Doc with
        a <pre> containing unformatted code.

        This is made easier because the generated HTML starts with a paragraph
        containing <span>&#60419;</span> and ends with a paragraph containing
        <span>&#60418;</span>
        """

        # The first line of a code block is identified by a <span> containing &#60419:
        for start_span in soup.find_all("span", string="\uEC03"):
            line_paras = []
            start_para: Tag = start_span.parent
            line_paras.append(start_para)
            start_span.decompose()  # Remove the span with the weird character

            # Add all the start paras siblings until one contains the end span:
            for para in start_para.next_siblings:
                # Ignore any whitespace between p tags.
                if isinstance(para, Tag):
                    line_paras.append(para)
                    end_span = para.find("span", string="\uEC02")
                    if end_span is not None:
                        end_span.decompose()  # Remove the span with the weird character
                        break
            code_content = "\n".join(
                flatten_html_line(line) for line in line_paras
            ).translate(str.maketrans("\xa0", " "))

            pre = soup.new_tag("pre")
            pre.string = code_content

            start_para.insert_before(pre)
            for line in line_paras:
                line.decompose()

            # Remove non-breaking spaces:
            # start_para.string = start_para.string.translate(str.maketrans("\xa0", " "))

    def fix_backticks(self, soup: BeautifulSoup):
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

    def remove_empty_paras(self, soup: BeautifulSoup):
        for tag in soup.find_all("span"):
            tag.unwrap()

        for tag in soup.find_all(lambda tag: tag.name == "p" and not tag.contents):
            tag.unwrap()


def default_log(msg):
    info(msg)


def process_google_doc_html(soup: BeautifulSoup, log=default_log):
    """
    Run all cleanup processes on the input HTML, modifying the input soup in-place.
    """

    cleaner = HTMLCleaner()
    log("Fixing single-cell tables")
    cleaner.remove_single_cell_tables(soup)
    log("Marking up Code Building Blocks")
    cleaner.process_building_block_code(soup)
    log("Marking code blocks")
    cleaner.mark_code_blocks(soup)
    log("Replacing style spans with <i> and <b>")
    cleaner.replace_style_spans(soup)
    log("Fixing Google's horrible indirect links")
    cleaner.fix_google_links(soup)
    log("Removing ids because they mess up the Markdown")
    cleaner.remove_ids(soup)
    log("Removing classes")
    cleaner.remove_classes(soup)
    log("Removing style attributes")
    cleaner.remove_styles(soup)
    log("Marking python code blocks as python")
    cleaner.identify_code_blocks(soup)
    log("Replacing backticks with <code> tags")
    cleaner.fix_backticks(soup)
    log("Removing empty paragraphs")
    cleaner.remove_empty_paras(soup)
