"""
Utilities shared by model APIs and training code.
"""
from typing import Any, Dict

import numpy as np


def normalize_feature_importance(importance: Dict[str, Any]) -> Dict[str, float]:
    """Return feature importance values sorted and normalized to 0-1."""
    cleaned = {}
    for feature, value in (importance or {}).items():
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(numeric_value):
            cleaned[str(feature)] = numeric_value

    total = sum(cleaned.values())
    if total > 0:
        cleaned = {feature: value / total for feature, value in cleaned.items()}

    return dict(sorted(cleaned.items(), key=lambda item: item[1], reverse=True))


def get_model_feature_importance(model_data: Dict[str, Any]) -> Dict[str, float]:
    """Read stored importance, or compute it from the loaded model for old files."""
    stored_importance = model_data.get("feature_importance")
    if stored_importance:
        return normalize_feature_importance(stored_importance)

    model = model_data.get("model")
    feature_names = model_data.get("feature_names") or []
    if model is None or not feature_names:
        return {}

    if hasattr(model, "feature_importances_"):
        raw_values = model.feature_importances_
    elif hasattr(model, "coef_"):
        raw_values = np.abs(model.coef_)
    else:
        return {}

    raw_values = np.asarray(raw_values, dtype=float).reshape(-1)
    length = min(len(feature_names), raw_values.size)
    importance = {
        feature_names[index]: raw_values[index]
        for index in range(length)
    }

    return normalize_feature_importance(importance)
