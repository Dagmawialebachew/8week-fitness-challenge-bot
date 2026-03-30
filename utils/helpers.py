# helpers.py
import logging
from typing import Any

def format_currency(amount: float, lang: str) -> str:
    """Formats price into ETB/Birr based on language."""
    if lang == "AM":
        return f"{amount:,.2f} ብር"
    return f"{amount:,.2f} ETB"

def clean_html(text: str) -> str:
    """Sanitizes text for MarkdownV2 or HTML if needed."""
    return text.replace("<", "&lt;").replace(">", "&gt;")

def log_admin_action(action: str, user_id: int, details: str):
    """Structured logging for admin-level events."""
    logging.info(f"ADMIN_LOG | User: {user_id} | Action: {action} | Details: {details}")

def get_product_key(lang: str, gender: str, level: str, freq: int) -> str:
    """Generates a unique string key for debugging or internal tracking."""
    return f"{lang}_{gender}_{level}_{freq}X"