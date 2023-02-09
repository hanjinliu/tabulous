from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
import json
from pathlib import Path
from tabulous.color import normalize_color


@dataclass(frozen=True)
class Style:
    background: str
    foreground: str
    base_color: str
    highlight0: str
    highlight1: str
    background0: str
    background1: str
    cell_highlight: str
    cell_selection: str

    @lru_cache(maxsize=12)
    def format_text(self, text: str) -> str:
        for name, value in asdict(self).items():
            text = text.replace(f"#[{name}]", f"{value}")
        return text

    def format_file(self, file: str | Path | None = None) -> str:
        if file is None:
            file = Path(__file__).parent / "_style.qss"
        with open(file) as f:
            text = f.read()
        return self.format_text(text)

    @classmethod
    def from_global(cls, name: str) -> Style:
        theme = GLOBAL_STYLES.get(name, None)
        if theme is None:
            raise ValueError(f"Theme {name!r} not found")
        js = asdict(theme)
        self = cls(**js)
        return self


GLOBAL_STYLES: dict[str, Style] = {}

with open(Path(__file__).parent / "defaults.json") as f:
    js: dict = json.load(f)
    for name, style in js.items():

        bg = normalize_color(style["background"])
        fg = normalize_color(style["foreground"])
        base = normalize_color(style["base_color"])
        if "background0" not in style:
            style["background0"] = bg.mix(fg, 0.1).html
        if "background1" not in style:
            style["background1"] = bg.mix(fg, -0.1).html
        if "highlight0" not in style:
            style["highlight0"] = base.mix(bg, 0.6).html
        if "highlight1" not in style:
            style["highlight1"] = base.mix(bg, 0.75).html
        if "cell_selection" not in style:
            style["cell_selection"] = base.html
        GLOBAL_STYLES[name] = Style(**style)
