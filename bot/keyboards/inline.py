# ============================
# WOLLOYEWA STORE BOT - INLINE KEYBOARDS
# ============================
"""Inline keyboard builders for inline button menus."""

from typing import List, Optional, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class InlineKeyboardBuilder:
    """Builder class for creating inline keyboards."""
    
    def __init__(self):
        self._keyboard: List[List[InlineKeyboardButton]] = []
    
    def add_button(
        self,
        text: str,
        callback_data: str,
        row: Optional[int] = None,
    ) -> "InlineKeyboardBuilder":
        """
        Add a button to the keyboard.
        
        Args:
            text: Button text
            callback_data: Callback data for the button
            row: Row index to add the button to (None = last row)
            
        Returns:
            Self for method chaining
        """
        button = InlineKeyboardButton(text, callback_data=callback_data)
        
        if row is not None and row < len(self._keyboard):
            self._keyboard[row].append(button)
        else:
            if not self._keyboard:
                self._keyboard.append([])
            self._keyboard[-1].append(button)
        
        return self
    
    def add_row(self) -> "InlineKeyboardBuilder":
        """Add a new empty row."""
        self._keyboard.append([])
        return self
    
    def add_buttons(self, buttons: List[tuple], row: Optional[int] = None) -> "InlineKeyboardBuilder":
        """
        Add multiple buttons.
        
        Args:
            buttons: List of (text, callback_data) tuples
            row: Row index to add buttons to
            
        Returns:
            Self for method chaining
        """
        for text, callback_data in buttons:
            self.add_button(text, callback_data, row)
        return self
    
    def build(self) -> InlineKeyboardMarkup:
        """Build and return the keyboard."""
        return InlineKeyboardMarkup(self._keyboard)
    
    def clear(self) -> "InlineKeyboardBuilder":
        """Clear the keyboard."""
        self._keyboard.clear()
        return self


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Create main menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("🛍️ ምርቶች", callback_data="menu_products")],
        [InlineKeyboardButton("🔍 ፈልግ", callback_data="menu_search")],
        [InlineKeyboardButton("🛒 ቅርጫት", callback_data="menu_cart")],
        [InlineKeyboardButton("👤 ፕሮፋይል", callback_data="menu_profile")],
        [InlineKeyboardButton("📦 ትዕዛዞቼ", callback_data="menu_orders")],
        [InlineKeyboardButton("⭐ ተመራጮች", callback_data="menu_wishlist")],
        [InlineKeyboardButton("❓ እገዛ", callback_data="menu_help")],
    ]
    return InlineKeyboardMarkup(keyboard)


def product_keyboard(
    product_id: int,
    in_stock: bool = True,
    in_wishlist: bool = False,
) -> InlineKeyboardMarkup:
    """
    Create product detail keyboard.
    
    Args:
        product_id: Product ID
        in_stock: Whether product is in stock
        in_wishlist: Whether product is in wishlist
    """
    keyboard = [
        [
            InlineKeyboardButton("🛒 ወደ ቅርጫት ጨምር", callback_data=f"add_to_cart_{product_id}"),
        ],
        [
            InlineKeyboardButton(
                "❤️ ከተመራጮች አውጣ" if in_wishlist else "❤️ ወደ ተመራጮች ጨምር",
                callback_data=f"remove_from_wishlist_{product_id}" if in_wishlist else f"add_to_wishlist_{product_id}",
            ),
        ],
        [
            InlineKeyboardButton("📝 ግምገማ ጻፍ", callback_data=f"review_{product_id}"),
            InlineKeyboardButton("🔙 ወደ ኋላ", callback_data="menu_back"),
        ],
    ]
    
    if not in_stock:
        keyboard[0][0] = InlineKeyboardButton("❌ ክምችት የለም", callback_data="out_of_stock")
    
    return InlineKeyboardMarkup(keyboard)


def cart_keyboard(has_items: bool = True) -> InlineKeyboardMarkup:
    """Create shopping cart keyboard."""
    if has_items:
        keyboard = [
            [
                InlineKeyboardButton("🗑️ ቅርጫትን አጥፋ", callback_data="cart_clear"),
                InlineKeyboardButton("🔄 አድስ", callback_data="cart_refresh"),
            ],
            [
                InlineKeyboardButton("✅ ግዢ አጠናቅቅ", callback_data="cart_checkout"),
                InlineKeyboardButton("➕ ቀጥል", callback_data="menu_products"),
            ],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("🛍️ ወደ ምርቶች", callback_data="menu_products")],
        ]
    
    return InlineKeyboardMarkup(keyboard)


def category_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """
    Create category selection keyboard.
    
    Args:
        categories: List of category dicts with 'id', 'name'
    """
    keyboard = []
    row = []
    
    for cat in categories:
        button = InlineKeyboardButton(cat["name"], callback_data=f"cat_{cat['id']}")
        row.append(button)
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 ወደ ምናሌ", callback_data="menu_back")])
    
    return InlineKeyboardMarkup(keyboard)


def pagination_keyboard(
    current_page: int,
    total_pages: int,
    base_callback: str,
    extra_buttons: Optional[List[tuple]] = None,
) -> InlineKeyboardMarkup:
    """
    Create pagination keyboard.
    
    Args:
        current_page: Current page number
        total_pages: Total number of pages
        base_callback: Base callback data (e.g., "products_page")
        extra_buttons: Additional buttons to add
    """
    keyboard = []
    
    # Pagination buttons
    pagination_row = []
    if current_page > 1:
        pagination_row.append(InlineKeyboardButton("◀️ ቀዳሚ", callback_data=f"{base_callback}_{current_page - 1}"))
    
    pagination_row.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    
    if current_page < total_pages:
        pagination_row.append(InlineKeyboardButton("ቀጣይ ▶️", callback_data=f"{base_callback}_{current_page + 1}"))
    
    keyboard.append(pagination_row)
    
    # Extra buttons
    if extra_buttons:
        for text, callback in extra_buttons:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback)])
    
    # Back button
    keyboard.append([InlineKeyboardButton("🔙 ወደ ኋላ", callback_data="menu_back")])
    
    return InlineKeyboardMarkup(keyboard)


def admin_keyboard() -> InlineKeyboardMarkup:
    """Create admin panel keyboard."""
    keyboard = [
        [InlineKeyboardButton("📊 ዳሽቦርድ", callback_data="admin_dashboard")],
        [InlineKeyboardButton("📦 ምርቶች", callback_data="admin_products")],
        [InlineKeyboardButton("📋 ትዕዛዞች", callback_data="admin_orders")],
        [InlineKeyboardButton("👥 ተጠቃሚዎች", callback_data="admin_users")],
        [InlineKeyboardButton("🏪 ሻጮች", callback_data="admin_vendors")],
        [InlineKeyboardButton("📊 ሪፖርቶች", callback_data="admin_reports")],
        [InlineKeyboardButton("⚙️ ቅንብሮች", callback_data="admin_settings")],
        [InlineKeyboardButton("🔙 ወደ ምናሌ", callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def yes_no_keyboard(callback_yes: str, callback_no: str) -> InlineKeyboardMarkup:
    """Create Yes/No confirmation keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("✅ አዎ", callback_data=callback_yes),
            InlineKeyboardButton("❌ አይ", callback_data=callback_no),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def rating_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Create rating keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("⭐", callback_data=f"rate_{product_id}_1"),
            InlineKeyboardButton("⭐⭐", callback_data=f"rate_{product_id}_2"),
            InlineKeyboardButton("⭐⭐⭐", callback_data=f"rate_{product_id}_3"),
            InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f"rate_{product_id}_4"),
            InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data=f"rate_{product_id}_5"),
        ],
        [InlineKeyboardButton("🔙 ሰርዝ", callback_data=f"cancel_review_{product_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)


__all__ = [
    "InlineKeyboardBuilder",
    "main_menu_keyboard",
    "product_keyboard",
    "cart_keyboard",
    "category_keyboard",
    "pagination_keyboard",
    "admin_keyboard",
    "yes_no_keyboard",
    "rating_keyboard",
]