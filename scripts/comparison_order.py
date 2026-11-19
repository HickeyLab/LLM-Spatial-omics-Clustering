"""Deterministic display ordering without changing any plotted observations."""
from __future__ import annotations

import numpy as np


def rank_labels(labels, scores, *, ascending=False):
    """Rank labels by a displayed summary, retaining input order for exact ties."""
    labels = list(labels)
    scores = np.asarray(scores, dtype=float)
    if scores.shape != (len(labels),) or not np.isfinite(scores).all():
        raise ValueError("Display-order scores must be one finite value per label")
    if len(set(labels)) != len(labels):
        raise ValueError("Display-order labels must be unique")
    positions = np.argsort(scores if ascending else -scores, kind="stable")
    return [labels[i] for i in positions]
