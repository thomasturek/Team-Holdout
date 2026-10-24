"""Leakage-free, point-in-time ML features over data/world.sqlite (SCOUT).

    from buyer.facts.features import build_feature_vector, FEATURE_COLUMNS
    build_feature_vector("sup:70110", "part:310010", "2026-09-30")

See FEATURES.md for every feature.
"""

from .extract import build_feature_vector
from .spec import CATEGORICAL, FEATURE_COLUMNS, ID_COLUMNS, NUMERIC, TARGET_COLUMNS
from .store import FeatureStore, default_store

__all__ = [
    "CATEGORICAL",
    "FEATURE_COLUMNS",
    "ID_COLUMNS",
    "NUMERIC",
    "TARGET_COLUMNS",
    "FeatureStore",
    "build_feature_vector",
    "default_store",
]
