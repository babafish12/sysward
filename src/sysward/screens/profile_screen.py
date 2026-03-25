"""Profile selection modal screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, Button, RadioButton, RadioSet


class ProfileScreen(ModalScreen[str | None]):
    """Modal for selecting a performance profile."""

    DEFAULT_CSS = """
    ProfileScreen {
        align: center middle;
    }
    ProfileScreen #dialog {
        width: 50;
        height: auto;
        padding: 1 2;
        border: round $primary;
        background: $surface;
    }
    ProfileScreen #title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    ProfileScreen RadioSet {
        margin-bottom: 1;
    }
    ProfileScreen #buttons {
        height: 3;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, profiles: dict[str, dict], active: str | None = None) -> None:
        super().__init__()
        self._profiles = profiles
        self._active = active

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Select Performance Profile", id="title")
            with RadioSet(id="profile-set"):
                for name in self._profiles:
                    display = name.replace("_", " ").title()
                    profile = self._profiles[name]
                    gov = profile.get("governor", "?")
                    turbo = "on" if profile.get("turbo", True) else "off"
                    epp = profile.get("epp", "?")
                    label = f"{display}  ({gov}, turbo={turbo}, epp={epp})"
                    yield RadioButton(label, value=name == self._active, name=name)
            yield Button("Apply", variant="primary", id="apply")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply":
            radio_set = self.query_one("#profile-set", RadioSet)
            if radio_set.pressed_button is not None:
                self.dismiss(radio_set.pressed_button.name)
            else:
                self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
