# ============================
# WOLLOYEWA STORE BOT - KEYBOARD BUILDER
# ============================
"""Universal keyboard builder for creating custom keyboards."""

from typing import List, Optional, Dict, Any, Callable
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import KeyboardButton, ReplyKeyboardMarkup


class KeyboardBuilder:
    """
    Universal keyboard builder for both inline and reply keyboards.
    
    Usage:
        # Inline keyboard
        keyboard = KeyboardBuilder.inline()
        keyboard.add_button("Click me", "callback_data")
        
        # Reply keyboard
        keyboard = KeyboardBuilder.reply()
        keyboard.add_button("Click me")
    """
    
    @staticmethod
    def inline(resize: bool = True) -> "InlineKeyboardBuilderWrapper":
        """Create an inline keyboard builder."""
        return InlineKeyboardBuilderWrapper()
    
    @staticmethod
    def reply(resize: bool = True, one_time: bool = False) -> "ReplyKeyboardBuilderWrapper":
        """Create a reply keyboard builder."""
        return ReplyKeyboardBuilderWrapper(resize, one_time)


class InlineKeyboardBuilderWrapper:
    """Wrapper for inline keyboard building."""
    
    def __init__(self):
        self._keyboard: List[List[InlineKeyboardButton]] = []
    
    def add_button(self, text: str, callback_data: str, row: Optional[int] = None) -> "InlineKeyboardBuilderWrapper":
        """Add a button to the keyboard."""
        button = InlineKeyboardButton(text, callback_data=callback_data)
        
        if row is not None and row < len(self._keyboard):
            self._keyboard[row].append(button)
        else:
            if not self._keyboard:
                self._keyboard.append([])
            self._keyboard[-1].append(button)
        
        return self
    
    def add_buttons(self, buttons: List[tuple], row: Optional[int] = None) -> "InlineKeyboardBuilderWrapper":
        """Add multiple buttons."""
        for text, callback in buttons:
            self.add_button(text, callback, row)
        return self
    
    def add_row(self) -> "InlineKeyboardBuilderWrapper":
        """Add a new row."""
        self._keyboard.append([])
        return self
    
    def build(self) -> InlineKeyboardMarkup:
        """Build the keyboard."""
        return InlineKeyboardMarkup(self._keyboard)
    
    def clear(self) -> "InlineKeyboardBuilderWrapper":
        """Clear the keyboard."""
        self._keyboard.clear()
        return self


class ReplyKeyboardBuilderWrapper:
    """Wrapper for reply keyboard building."""
    
    def __init__(self, resize: bool = True, one_time: bool = False):
        self._keyboard: List[List[KeyboardButton]] = []
        self.resize = resize
        self.one_time = one_time
    
    def add_button(self, text: str, row: Optional[int] = None, request_contact: bool = False, request_location: bool = False) -> "ReplyKeyboardBuilderWrapper":
        """Add a button to the keyboard."""
        button = KeyboardButton(text, request_contact=request_contact, request_location=request_location)
        
        if row is not None and row < len(self._keyboard):
            self._keyboard[row].append(button)
        else:
            if not self._keyboard:
                self._keyboard.append([])
            self._keyboard[-1].append(button)
        
        return self
    
    def add_buttons(self, buttons: List[str], row: Optional[int] = None) -> "ReplyKeyboardBuilderWrapper":
        """Add multiple buttons."""
        for text in buttons:
            self.add_button(text, row)
        return self
    
    def add_row(self) -> "ReplyKeyboardBuilderWrapper":
        """Add a new row."""
        self._keyboard.append([])
        return self
    
    def build(self) -> ReplyKeyboardMarkup:
        """Build the keyboard."""
        return ReplyKeyboardMarkup(
            self._keyboard,
            resize_keyboard=self.resize,
            one_time_keyboard=self.one_time,
        )
    
    def clear(self) -> "ReplyKeyboardBuilderWrapper":
        """Clear the keyboard."""
        self._keyboard.clear()
        return self


def build_menu(
    buttons: List[Any],
    n_cols: int = 2,
    header_buttons: Optional[List[Any]] = None,
    footer_buttons: Optional[List[Any]] = None,
) -> List[List[Any]]:
    """
    Build a menu grid from a list of buttons.
    
    Args:
        buttons: List of buttons
        n_cols: Number of columns
        header_buttons: Buttons to add at the top
        footer_buttons: Buttons to add at the bottom
        
    Returns:
        2D list of buttons
    """
    menu = []
    
    if header_buttons:
        menu.append(header_buttons)
    
    for i in range(0, len(buttons), n_cols):
        menu.append(buttons[i:i + n_cols])
    
    if footer_buttons:
        menu.append(footer_buttons)
    
    return menu


def build_pagination(
    current_page: int,
    total_pages: int,
    callback_prefix: str,
    extra_buttons: Optional[List[tuple]] = None,
) -> InlineKeyboardMarkup:
    """
    Build a pagination keyboard.
    
    Args:
        current_page: Current page number
        total_pages: Total number of pages
        callback_prefix: Prefix for callback data
        extra_buttons: Additional buttons
        
    Returns:
        InlineKeyboardMarkup
    """
    keyboard = []
    
    # Pagination row
    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton("◀️", callback_data=f"{callback_prefix}_{current_page - 1}"))
    
    pagination_row.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton("▶️", callback_data=f"{callback_prefix}_{current_page + 1}"))
    
    keyboard.append(pagination_row)
    
    # Extra buttons
    if extra_buttons:
        for text, callback in extra_buttons:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback)])
    
    return InlineKeyboardMarkup(keyboard)


def build_product_grid(
    products: List[Dict[str, Any]],
    items_per_row: int = 2,
) -> InlineKeyboardMarkup:
    """
    Build a product grid keyboard.
    
    Args:
        products: List of product dicts with 'id', 'name'
        items_per_row: Number of items per row
        
    Returns:
        InlineKeyboardMarkup
    """
    keyboard = []
    row = []
    
    for product in products:
        button = InlineKeyboardButton(
            f"📦 {product['name'][:20]}",
            callback_data=f"prod_{product['id']}"
        )
        row.append(button)
        
        if len(row) == items_per_row:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)


def build_category_list(
    categories: List[Dict[str, Any]],
    items_per_row: int = 2,
) -> InlineKeyboardMarkup:
    """
    Build a category list keyboard.
    
    Args:
        categories: List of category dicts with 'id', 'name'
        items_per_row: Number of items per row
        
    Returns:
        InlineKeyboardMarkup
    """
    keyboard = []
    row = []
    
    for category in categories:
        button = InlineKeyboardButton(
            f"📁 {category['name']}",
            callback_data=f"cat_{category['id']}"
        )
        row.append(button)
        
        if len(row) == items_per_row:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)


__all__ = [
    "KeyboardBuilder",
    "InlineKeyboardBuilderWrapper",
    "ReplyKeyboardBuilderWrapper",
    "build_menu",
    "build_pagination",
    "build_product_grid",
    "build_category_list",
]