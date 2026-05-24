# ============================
# WOLLOYEWA STORE BOT - KEYBOARD TESTS
# ============================
"""Tests for bot keyboard builders."""

import pytest
from telegram import InlineKeyboardButton, KeyboardButton


@pytest.mark.unit
class TestInlineKeyboards:
    """Tests for inline keyboard builders."""
    
    def test_main_menu_keyboard(self):
        """Test main menu keyboard creation."""
        from bot.keyboards.inline import main_menu_keyboard
        
        keyboard = main_menu_keyboard()
        
        assert keyboard is not None
        # Main menu should have 7 buttons
        assert len(keyboard.inline_keyboard) >= 7
    
    def test_product_keyboard_in_stock(self):
        """Test product keyboard when in stock."""
        from bot.keyboards.inline import product_keyboard
        
        keyboard = product_keyboard(product_id=1, in_stock=True, in_wishlist=False)
        
        assert keyboard is not None
        # Should have add to cart button
        buttons = keyboard.inline_keyboard
        assert len(buttons) >= 1
    
    def test_product_keyboard_out_of_stock(self):
        """Test product keyboard when out of stock."""
        from bot.keyboards.inline import product_keyboard
        
        keyboard = product_keyboard(product_id=1, in_stock=False)
        
        assert keyboard is not_error
        # Should show out of stock button
        first_button = keyboard.inline_keyboard[0][0]
        assert "ክምችት" in first_button.text
    
    def test_cart_keyboard_with_items(self):
        """Test cart keyboard when cart has items."""
        from bot.keyboards.inline import cart_keyboard
        
        keyboard = cart_keyboard(has_items=True)
        
        assert keyboard is not None
        # Should have checkout button
        buttons = keyboard.inline_keyboard
        assert len(buttons) >= 1
    
    def test_cart_keyboard_empty(self):
        """Test cart keyboard when cart is empty."""
        from bot.keyboards.inline import cart_keyboard
        
        keyboard = cart_keyboard(has_items=False)
        
        assert keyboard is not None
        # Should only have back button
        assert len(keyboard.inline_keyboard) == 1
    
    def test_category_keyboard(self):
        """Test category keyboard creation."""
        from bot.keyboards.inline import category_keyboard
        
        categories = [
            {"id": 1, "name": "Electronics"},
            {"id": 2, "name": "Clothing"},
        ]
        keyboard = category_keyboard(categories)
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) >= 1
    
    def test_pagination_keyboard(self):
        """Test pagination keyboard creation."""
        from bot.keyboards.inline import pagination_keyboard
        
        keyboard = pagination_keyboard(
            current_page=2,
            total_pages=5,
            base_callback="products_page",
        )
        
        assert keyboard is not None
        # Should have pagination buttons
        assert len(keyboard.inline_keyboard) >= 1
    
    def test_admin_keyboard(self):
        """Test admin keyboard creation."""
        from bot.keyboards.inline import admin_keyboard
        
        keyboard = admin_keyboard()
        
        assert keyboard is not None
        # Admin menu should have multiple buttons
        assert len(keyboard.inline_keyboard) >= 5
    
    def test_yes_no_keyboard(self):
        """Test yes/no confirmation keyboard."""
        from bot.keyboards.inline import yes_no_keyboard
        
        keyboard = yes_no_keyboard("confirm_yes", "confirm_no")
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2
    
    def test_rating_keyboard(self):
        """Test rating keyboard creation."""
        from bot.keyboards.inline import rating_keyboard
        
        keyboard = rating_keyboard(product_id=1)
        
        assert keyboard is not None
        # Should have 5 rating buttons
        assert len(keyboard.inline_keyboard) >= 1


@pytest.mark.unit
class TestReplyKeyboards:
    """Tests for reply keyboard builders."""
    
    def test_main_reply_keyboard(self):
        """Test main reply keyboard creation."""
        from bot.keyboards.reply import main_reply_keyboard
        
        keyboard = main_reply_keyboard()
        
        assert keyboard is not None
        assert keyboard.resize_keyboard is True
    
    def test_contact_keyboard(self):
        """Test contact sharing keyboard."""
        from bot.keyboards.reply import contact_keyboard
        
        keyboard = contact_keyboard()
        
        assert keyboard is not None
        assert keyboard.one_time_keyboard is True
    
    def test_location_keyboard(self):
        """Test location sharing keyboard."""
        from bot.keyboards.reply import location_keyboard
        
        keyboard = location_keyboard()
        
        assert keyboard is not None
        assert keyboard.resize_keyboard is True
    
    def test_admin_reply_keyboard(self):
        """Test admin reply keyboard."""
        from bot.keyboards.reply import admin_reply_keyboard
        
        keyboard = admin_reply_keyboard()
        
        assert keyboard is not None
        assert keyboard.resize_keyboard is True
    
    def test_cancel_keyboard(self):
        """Test cancel keyboard."""
        from bot.keyboards.reply import cancel_keyboard
        
        keyboard = cancel_keyboard()
        
        assert keyboard is not None
        assert len(keyboard.keyboard) == 1
    
    def test_remove_keyboard(self):
        """Test keyboard removal."""
        from bot.keyboards.reply import remove_keyboard
        
        remove = remove_keyboard()
        
        assert remove is not None
    
    def test_number_keyboard(self):
        """Test number selection keyboard."""
        from bot.keyboards.reply import number_keyboard
        
        keyboard = number_keyboard()
        
        assert keyboard is not None
        # Should have number buttons 0-9
        assert len(keyboard.keyboard) >= 4


@pytest.mark.unit
class TestKeyboardBuilder:
    """Tests for keyboard builder class."""
    
    def test_inline_builder_add_button(self):
        """Test inline builder button addition."""
        from bot.keyboards.builder import KeyboardBuilder
        
        builder = KeyboardBuilder.inline()
        builder.add_button("Test", "test_callback")
        
        keyboard = builder.build()
        assert keyboard is not None
    
    def test_inline_builder_add_row(self):
        """Test inline builder row addition."""
        from bot.keyboards.builder import KeyboardBuilder
        
        builder = KeyboardBuilder.inline()
        builder.add_button("Button1", "cb1")
        builder.add_row()
        builder.add_button("Button2", "cb2")
        
        keyboard = builder.build()
        assert len(keyboard.inline_keyboard) >= 2
    
    def test_reply_builder_add_button(self):
        """Test reply builder button addition."""
        from bot.keyboards.builder import KeyboardBuilder
        
        builder = KeyboardBuilder.reply()
        builder.add_button("Test")
        
        keyboard = builder.build()
        assert keyboard is not None
    
    def test_build_menu(self):
        """Test build_menu helper."""
        from bot.keyboards.builder import build_menu
        
        buttons = [1, 2, 3, 4, 5]
        menu = build_menu(buttons, n_cols=2)
        
        assert len(menu) == 3  # 5 buttons in 3 rows (2,2,1)
    
    def test_build_pagination(self):
        """Test build_pagination helper."""
        from bot.keyboards.builder import build_pagination
        
        keyboard = build_pagination(1, 10, "test_page")
        
        assert keyboard is not None
    
    def test_build_product_grid(self):
        """Test build_product_grid helper."""
        from bot.keyboards.builder import build_product_grid
        
        products = [
            {"id": 1, "name": "Product 1"},
            {"id": 2, "name": "Product 2"},
        ]
        keyboard = build_product_grid(products)
        
        assert keyboard is not None
    
    def test_build_category_list(self):
        """Test build_category_list helper."""
        from bot.keyboards.builder import build_category_list
        
        categories = [
            {"id": 1, "name": "Category 1"},
            {"id": 2, "name": "Category 2"},
        ]
        keyboard = build_category_list(categories)
        
        assert keyboard is not None


__all__ = ["TestInlineKeyboards", "TestReplyKeyboards", "TestKeyboardBuilder"]