from argparse import ArgumentParser
import logging
from logging import info
from pathlib import Path
from subprocess import Popen, PIPE
import sys

from bs4 import BeautifulSoup
import mdformat

from . import (
    mark_code_blocks,
    replace_style_spans,
    fix_google_links,
    fix_backticks,
    remove_ids,
    remove_classes,
    remove_empty_paras,
    remove_styles,
    identify_code_blocks,
    remove_single_cell_tables,
)


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
    remove_single_cell_tables(soup)
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
