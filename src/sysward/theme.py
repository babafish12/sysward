"""Theme presets for Sysward — reused from ssh-term."""

from __future__ import annotations

from textual.theme import Theme

THEMES: list[Theme] = [
    Theme(
        name="tokyo-night",
        primary="#7aa2f7",
        secondary="#9ece6a",
        accent="#bb9af7",
        warning="#e0af68",
        error="#f7768e",
        success="#9ece6a",
        foreground="#c0caf5",
        background="#1a1b26",
        surface="#24283b",
        panel="#414868",
        dark=True,
        variables={"highlight": "#292e42", "info": "#7dcfff"},
    ),
    Theme(
        name="catppuccin-mocha",
        primary="#89b4fa",
        secondary="#a6e3a1",
        accent="#cba6f7",
        warning="#f9e2af",
        error="#f38ba8",
        success="#a6e3a1",
        foreground="#cdd6f4",
        background="#1e1e2e",
        surface="#313244",
        panel="#45475a",
        dark=True,
        variables={"highlight": "#313244", "info": "#89dceb"},
    ),
    Theme(
        name="dracula",
        primary="#bd93f9",
        secondary="#50fa7b",
        accent="#ff79c6",
        warning="#f1fa8c",
        error="#ff5555",
        success="#50fa7b",
        foreground="#f8f8f2",
        background="#282a36",
        surface="#44475a",
        panel="#6272a4",
        dark=True,
        variables={"highlight": "#44475a", "info": "#8be9fd"},
    ),
    Theme(
        name="nord",
        primary="#88c0d0",
        secondary="#a3be8c",
        accent="#b48ead",
        warning="#ebcb8b",
        error="#bf616a",
        success="#a3be8c",
        foreground="#eceff4",
        background="#2e3440",
        surface="#3b4252",
        panel="#4c566a",
        dark=True,
        variables={"highlight": "#3b4252", "info": "#81a1c1"},
    ),
    Theme(
        name="gruvbox-dark",
        primary="#83a598",
        secondary="#b8bb26",
        accent="#d3869b",
        warning="#fabd2f",
        error="#fb4934",
        success="#b8bb26",
        foreground="#ebdbb2",
        background="#282828",
        surface="#3c3836",
        panel="#504945",
        dark=True,
        variables={"highlight": "#3c3836", "info": "#83a598"},
    ),
    Theme(
        name="one-dark",
        primary="#61afef",
        secondary="#98c379",
        accent="#c678dd",
        warning="#e5c07b",
        error="#e06c75",
        success="#98c379",
        foreground="#abb2bf",
        background="#282c34",
        surface="#3e4451",
        panel="#4b5263",
        dark=True,
        variables={"highlight": "#3e4451", "info": "#56b6c2"},
    ),
]

THEME_NAMES: list[str] = [t.name for t in THEMES]


def get_color(theme_name: str, color_name: str) -> str:
    """Get a hex color value from a registered theme by name."""
    for t in THEMES:
        if t.name == theme_name:
            val = getattr(t, color_name, None)
            if val is not None:
                return str(val)
            return t.variables.get(color_name, "#c0caf5")
    return "#c0caf5"


def next_theme(current: str) -> str:
    idx = THEME_NAMES.index(current) if current in THEME_NAMES else -1
    return THEME_NAMES[(idx + 1) % len(THEME_NAMES)]
