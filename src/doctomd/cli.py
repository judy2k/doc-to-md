from argparse import ArgumentParser
import logging
from logging import info
from pathlib import Path
from subprocess import Popen, PIPE
import sys

from bs4 import BeautifulSoup
import mdformat
from rich.console import Console
from rich.logging import RichHandler

from . import process_google_doc_html

def main(argv=sys.argv[1:]):
    console = Console(stderr=True, highlight=False)
    logging.basicConfig(
        format="%(message)s",
        level=logging.NOTSET,
        datefmt="[%X]",
        handlers=[RichHandler(console=console)],
    )
    logging.getLogger("markdown_it").setLevel(logging.WARN)

    try:
        ap = ArgumentParser(prog="doc2md", description=__doc__)
        ap.add_argument("input", type=Path)
        ap.add_argument("output", type=Path)
        ap.add_argument(
            "--no-pandoc",
            action="store_true",
            help="Output will be cleaned HTML instead of Markdown. This option is primarily for debugging.",
        )
        ap.add_argument(
            "--no-format",
            action="store_true",
            help="Output will not be reformatted with mdformat. If --no-pandoc is supplied, then this option does nothing.",
        )
        ap.add_argument(
            "-v",
            "--verbose",
            action="count",
            default=0,
            help="Increase the amount of output describing the operation of doc2md. This flag can be repeated to increase verbosity even more.",
        )

        args = ap.parse_args(argv)

        log_level = {0: logging.WARN, 1: logging.INFO}.get(args.verbose, logging.DEBUG)
        logging.getLogger().setLevel(log_level)

        path: Path = args.input
        output_path: Path = args.output

        if not path.exists():
            ap.error(f"The input file {path} does not exist")
        if path.is_dir():
            ap.error(f"Input path {path} should be a file, not a directory")

        if output_path.is_dir():
            ap.error(f"Output path is a directory, which is not supported.")
        if not output_path.parent.is_dir() and not output_path.parent.is_symlink():
            ap.error(
                f"Can't write to path {output_path.parent} because it doesn't exist or isn't a directory."
            )

        soup = BeautifulSoup(path.read_text(), "lxml")

        with console.status("Pre-processing HTML"):
            process_google_doc_html(soup, log=console.out)

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
        with console.status("Converting to Markdown"):
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
    except KeyboardInterrupt:
        pass
    except Exception:
        console.print_exception(show_locals=False)
