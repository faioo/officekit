"""Command-line interface for the DOI query tool."""

from __future__ import annotations

import argparse
from pathlib import Path

from officekit.tools.doi_query.core import enrich_excel_with_doi


def run_interactive() -> None:
    """Prompt for options and run DOI enrichment."""
    input_path = input("请输入 Excel 文件路径：").strip()
    output_path = input("请输入输出文件路径（留空则自动生成）：").strip() or None
    sheet_name = input("请输入工作表名称（留空则使用当前活动表）：").strip() or None

    summary = enrich_excel_with_doi(input_path, output_path, sheet_name=sheet_name)
    _print_summary(summary)


def main(argv: list[str] | None = None) -> None:
    """Run DOI enrichment from command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Query Crossref DOI values for an Excel file with Title, Journal, and Year columns."
    )
    parser.add_argument("input_path", help="Path to the .xlsx file.")
    parser.add_argument("-o", "--output-path", help="Path for the enriched output workbook.")
    parser.add_argument("--sheet", help="Worksheet name. Defaults to the active sheet.")
    parser.add_argument("--timeout", type=int, default=30, help="Crossref request timeout in seconds.")
    args = parser.parse_args(argv)

    summary = enrich_excel_with_doi(
        Path(args.input_path),
        Path(args.output_path) if args.output_path else None,
        sheet_name=args.sheet,
        timeout=args.timeout,
    )
    _print_summary(summary)


def _print_summary(summary) -> None:
    print("处理完成！")
    print(f"总记录数: {summary.total}")
    print(f"成功找到 DOI: {summary.success}")
    print(f"未找到 DOI: {summary.not_found}")
    print(f"查询出错: {summary.errors}")
    print(f"输出文件: {summary.output_path}")


if __name__ == "__main__":
    main()
