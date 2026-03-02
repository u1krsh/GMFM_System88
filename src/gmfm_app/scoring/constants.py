"""GMFM domain/item constants backed by the official score sheet catalog."""

from gmfm_app.scoring.items_catalog import build_item_number_map

# Lazy-load to avoid crashing the entire import chain if data file is missing
_gmfm88 = None


def _ensure_loaded():
    global _gmfm88
    if _gmfm88 is None:
        _gmfm88 = build_item_number_map("88")


class _LazyItems:
    """Lazy dict-like that loads on first access so import never crashes."""
    def __init__(self, scale):
        self._scale = scale
        self._data = None
    
    def _load(self):
        if self._data is None:
            self._data = build_item_number_map(self._scale)
        return self._data

    def items(self):
        return self._load().items()

    def keys(self):
        return self._load().keys()

    def values(self):
        return self._load().values()

    def get(self, key, default=None):
        return self._load().get(key, default)

    def __getitem__(self, key):
        return self._load()[key]

    def __contains__(self, key):
        return key in self._load()

    def __iter__(self):
        return iter(self._load())

    def __len__(self):
        return len(self._load())


GMFM88_ITEMS = _LazyItems("88")

# Maximum score per item (0-3 per manual)
MAX_ITEM_SCORE = 3
