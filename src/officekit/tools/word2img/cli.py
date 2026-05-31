"""Command-line interface for the Word to image tool."""

from __future__ import annotations

import argparse
from pathlib import Path

from officekit.tools.word2img.core import convert_word_to_images


def run_interactive() -> None:
    """Prompt for conversion options and run the Word to image tool."""
    input_path = input("请输入 Word 文档路径：").strip()
    output_dir = input("请输入图片输出目录（留空则输出到文档同级目录）：").strip() or None

    images = convert_word_to_images(input_path, output_dir)
    print(f"已生成 {len(images)} 张图片：")
    for image in images:
        print(f"- {image}")


def main(argv: list[str] | None = None) -> None:
    """Run the Word to image tool from command-line arguments."""
    parser = argparse.ArgumentParser(description="Convert a Word document to page images.")
    parser.add_argument("input_path", help="Path to the .doc or .docx file.")
    parser.add_argument("-o", "--output-dir", help="Directory where generated images are written.")
    parser.add_argument("--format", choices=["png", "jpeg"], default="png", help="Output image format.")
    parser.add_argument("--dpi", type=int, default=150, help="Output image resolution.")
    args = parser.parse_args(argv)

    images = convert_word_to_images(
        Path(args.input_path),
        Path(args.output_dir) if args.output_dir else None,
        image_format=args.format,
        dpi=args.dpi,
    )

    for image in images:
        print(image)


if __name__ == "__main__":
    main()
