"""GMFM domain/item constants backed by the official score sheet catalog."""

from gmfm_app.scoring.items_catalog import build_item_number_map


GMFM66_ITEMS = build_item_number_map("66")
GMFM88_ITEMS = build_item_number_map("88")

# Maximum score per item (0-3 per manual)
MAX_ITEM_SCORE = 3
