import argparse
import sys
from pathlib import Path

from PIL import Image


def make_icon(input_path: Path, output_path: Path, resolutions: list[int]):
    input_image = Image.open(input_path)
    input_image.save(
        output_path.open("wb"),
        format="icns",
        append_images=[input_image.resize((res, res)) for res in resolutions],
    )


def intlist(ss: str):
    return sorted(map(int, ss.split(",")), reverse=True)


def main(argv=sys.argv[1:]):
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("resolutions", type=intlist)

    args = ap.parse_args(argv)
    make_icon(args.input, args.output, args.resolutions)


if __name__ == "__main__":
    main()
