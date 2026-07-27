"""Couche d'interface Streamlit.

Chaque module expose une fonction `render()` sans argument. C'est la seule
partie du projet qui importe Streamlit : la logique métier reste testable et
réutilisable indépendamment.
"""

from . import page_history, page_pantry, page_profile, page_suggest, page_today

__all__ = ["page_history", "page_pantry", "page_profile", "page_suggest", "page_today"]
