from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "evidence" / "visual-qa-r9" / "pages-144dpi"


def page_number(path: Path) -> int:
    return int(path.stem.rsplit("-", 1)[1])


def main() -> None:
    paths = sorted(PAGES.glob("page-*.png"), key=page_number)
    failures: list[dict[str, object]] = []
    for path in paths:
        try:
            with Image.open(path) as image:
                image.verify()
        except Exception as error:  # exact diagnostic is part of the bounded audit output
            failures.append(
                {
                    "page_one_based": page_number(path),
                    "path": path.name,
                    "bytes": path.stat().st_size,
                    "exception": type(error).__name__,
                    "message": str(error),
                }
            )
    print(json.dumps({"files": len(paths), "failures": failures}, ensure_ascii=False))


if __name__ == "__main__":
    main()
