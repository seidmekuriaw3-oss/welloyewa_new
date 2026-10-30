# ============================
# WOLLOYEWA STORE BOT - REPLY KEYBOARDS
# ============================
"""Reply keyboard builders for text-based menus."""

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo

from bot.localization import translate
from core.config import settings


class ReplyKeyboardBuilder:
    """Builder class for creating reply keyboards."""

    def __init__(self, resize_keyboard: bool = True, one_time_keyboard: bool = False):
        self._keyboard: list[list[KeyboardButton]] = []
        self.resize_keyboard = resize_keyboard
        self.one_time_keyboard = one_time_keyboard

    def add_button(self, text: str, row: int | None = None) -> "ReplyKeyboardBuilder":
        """
        Add a button to the keyboard.

        Args:
            text: Button text
            row: Row index to add the button to (None = last row)

        Returns:
            Self for method chaining
        """
        button = KeyboardButton(text)

        if row is not None and row < len(self._keyboard):
            self._keyboard[row].append(button)
        else:
            if not self._keyboard:
                self._keyboard.append([])
            self._keyboard[-1].append(button)

        return self

    def add_row(self) -> "ReplyKeyboardBuilder":
        """Add a new empty row."""
        self._keyboard.append([])
        return self

    def add_buttons(self, buttons: list[str], row: int | None = None) -> "ReplyKeyboardBuilder":
        """
        Add multiple buttons.

        Args:
            buttons: List of button texts
            row: Row index to add buttons to

        Returns:
            Self for method chaining
        """
        for text in buttons:
            self.add_button(text, row)
        return self

    def build(self) -> ReplyKeyboardMarkup:
        """Build and return the keyboard."""
        return ReplyKeyboardMarkup(
            self._keyboard,
            resize_keyboard=self.resize_keyboard,
            one_time_keyboard=self.one_time_keyboard,
        )

    def clear(self) -> "ReplyKeyboardBuilder":
        """Clear the keyboard."""
        self._keyboard.clear()
        return self


def main_reply_keyboard(lang: str = "am") -> ReplyKeyboardMarkup:
    """Create the five-row localized home menu with a dedicated Mini App button."""
    web_app_url = settings.web_app_url
    web_app_button = KeyboardButton(
        translate(lang, "web_app"),
        web_app=WebAppInfo(url=web_app_url)
        if web_app_url.lower().startswith("https://")
        else None,
    )
    keyboard = [
        [translate(lang, "browse_store"), web_app_button],
        [translate(lang, "home_cart"), translate(lang, "home_wishlist")],
        [translate(lang, "home_search"), translate(lang, "orders")],
        [translate(lang, "home_profile"), translate(lang, "vendor_panel")],
        [translate(lang, "home_help")],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
    )


def main_reply_button_actions() -> dict[str, str]:
    """Map every localized main-menu button label to its routing action."""
    actions: dict[str, str] = {}
    for language in ("am", "en", "om"):
        for label_key, action in (
            ("browse_store", "browse_store"),
            ("web_app", "web_app"),
            ("home_cart", "cart"),
            ("home_wishlist", "wishlist"),
            ("home_search", "search"),
            ("orders", "orders"),
            ("home_profile", "profile"),
            ("vendor_panel", "vendor_panel"),
            ("home_help", "help"),
        ):
            actions[translate(language, label_key)] = action
    return actions


def contact_keyboard(lang: str = "am") -> ReplyKeyboardMarkup:
    """Create keyboard with contact sharing button."""
    keyboard = [
        [KeyboardButton(translate(lang, "phone_share"), request_contact=True)],
        [translate(lang, "back")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def location_keyboard(lang: str = "am") -> ReplyKeyboardMarkup:
    """Create keyboard with location sharing button."""
    keyboard = [
        [KeyboardButton(translate(lang, "location_share"), request_location=True)],
        [translate(lang, "enter_city")],
        [translate(lang, "back")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def admin_reply_keyboard(lang: str = "am") -> ReplyKeyboardMarkup:
    """Create the localized admin reply keyboard."""
    keyboard = [
        [translate(lang, "admin"), translate(lang, "products")],
        [translate(lang, "orders"), translate(lang, "vendors")],
        [translate(lang, "reports"), translate(lang, "help")],
        [translate(lang, "settings"), translate(lang, "home")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def cancel_keyboard(lang: str = "am") -> ReplyKeyboardMarkup:
    """Create a localized cancel keyboard."""
    keyboard = [[translate(lang, "cancel")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def remove_keyboard() -> ReplyKeyboardRemove:
    """Return a keyboard removal object."""
    return ReplyKeyboardRemove()


def number_keyboard(lang: str = "am") -> ReplyKeyboardMarkup:
    """Create number selection keyboard (1-9)."""
    keyboard = [
        ["1", "2", "3"],
        ["4", "5", "6"],
        ["7", "8", "9"],
        ["0", translate(lang, "cancel")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


__all__ = [
    "ReplyKeyboardBuilder",
    "admin_reply_keyboard",
    "cancel_keyboard",
    "contact_keyboard",
    "location_keyboard",
    "main_reply_button_actions",
    "main_reply_keyboard",
    "number_keyboard",
    "remove_keyboard",
]
