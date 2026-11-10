"""Render the bundled SVG mark into a multi-resolution Windows ICO."""
import argparse
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    renderer = QSvgRenderer(QByteArray(args.source.read_bytes()))
    if not renderer.isValid():
        raise SystemExit(f"Invalid SVG icon: {args.source}")
    image = QImage(QSize(256, 256), QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    args.destination.parent.mkdir(parents=True, exist_ok=True)
    png = args.destination.with_suffix(".png")
    if not image.save(str(png), "PNG"):
        raise SystemExit("Could not render SVG icon.")
    with Image.open(png) as rendered:
        rendered.convert("RGBA").save(
            args.destination, format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
    png.unlink()


if __name__ == "__main__":
    main()
