from argparse import ArgumentParser
import logging
from logging import info, Handler, LogRecord
from pathlib import Path
import sys

from rich.console import Console
from rich.logging import RichHandler

import toga
from toga.style.pack import COLUMN, ROW

from bs4 import BeautifulSoup

from . import process_google_doc_html, do_pandoc_pypandoc


class LogWidgetHandler(Handler):
    def __init__(self, text_widget: toga.MultilineTextInput):
        super().__init__()
        self._multiline = text_widget

    def emit(self, record: LogRecord):
        self._multiline.app.loop.call_soon(self.emit_in_loop, record)

    def emit_in_loop(self, record: LogRecord):
        self._multiline.value += record.getMessage() + "\n"
        self._multiline.scroll_to_bottom()


def do_conversion(input_path, output_path):
    def converter():
        soup = BeautifulSoup(Path(input_path).read_text(), "lxml")

        info("Pre-processing HTML")
        process_google_doc_html(soup)

        info("Converting to Markdown")
        do_pandoc_pypandoc(soup, Path(output_path), True)

        info("Done.")

    return converter


class DocConverter(toga.App):
    input_file: str = None

    def __init__(self, input=None):
        self.input_file = input

        super().__init__(
            "Google Doc Converter",
            "judy2k.gdoc2md",
            startup=DocConverter._build,
            icon="resources/app_icon.png",
        )

    def _build(self):
        # Components
        root_box = toga.Box()
        body_box = toga.Box()

        banner = toga.ImageView(toga.Image("resources/banner.png"))

        self.convert_button = convert_button = toga.Button("Convert")
        convert_button.style.padding_top = 10

        log_text = toga.MultilineTextInput(readonly=True)
        log_text.style.update(background_color="#ffffff", padding_top=10, flex=True)

        # Events:
        logging.getLogger().addHandler(LogWidgetHandler(log_text))

        async def on_convert(button: toga.Button):
            output_path = await self.main_window.save_file_dialog(
                "Save Markdown file …", "output.md", file_types=["md", "markdown"]
            )
            info(f"Output Path: {output_path}")
            if output_path is not None:
                await self.loop.run_in_executor(
                    None, do_conversion(self.input_file_text_input.value, output_path)
                )

        convert_button.on_press = on_convert

        # Layout:
        body_box.add(self._input_widgets())
        body_box.add(convert_button)
        body_box.add(log_text)
        body_box.style.update(direction=COLUMN, padding=10, flex=True)

        # Compose:
        root_box.add(banner)
        root_box.add(body_box)

        root_box.style.update(direction=COLUMN)

        # Initial state:
        self.set_input_path(self.input_file)

        return root_box

    def set_input_path(self, value: str | None):
        self.input_file_text_input.value = value
        self.convert_button.enabled = value is not None

    def _input_widgets(self):
        # Components:
        input_file_path_label = toga.Label("Google Doc (Exported HTML):")
        self.input_file_text_input = input_file_text_input = toga.TextInput(
            readonly=True
        )
        input_file_text_input.style.flex = 1
        input_file_text_input.style.padding = (0, 5)
        select_input = toga.Button("Open …")

        # Events:
        async def on_open(button: toga.Button):
            print("open")
            selected_path = await self.main_window.open_file_dialog(
                "Select HTML file", file_types=["html", "htm"]
            )
            info(f"Selected Path: {selected_path}")
            if selected_path is not None:
                self.set_input_path(selected_path)

        select_input.on_press = on_open

        # Layout:
        box = toga.Box()
        box.style.update(direction=ROW)

        box.add(input_file_path_label)
        box.add(input_file_text_input)
        box.add(select_input)

        return box


def main(argv=sys.argv[1:]):
    console = Console(stderr=True, highlight=False)
    logging.basicConfig(
        format="%(name)s %(message)s",
        level=logging.INFO,
        datefmt="[%X]",
        handlers=[RichHandler(console=console)],
    )
    logging.getLogger("markdown_it").setLevel(logging.WARN)
    logging.getLogger("pypandoc").setLevel(logging.WARN)
    logging.getLogger("css_parser").setLevel(logging.WARN)

    try:
        ap = ArgumentParser(prog="doc2md", description=__doc__)
        ap.add_argument("input", type=Path, nargs="?")

        args = ap.parse_args(argv)

        return DocConverter(input=args.input).main_loop()
    except KeyboardInterrupt:
        pass
    except Exception:
        console.print_exception(show_locals=False)
