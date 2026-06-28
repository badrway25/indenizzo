"""Small, safe template helpers for the public templates (P29)."""

from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def dict_get(mapping, key):
    """Look up ``mapping[key]`` from a template (returns the key if absent).

    Lets a template render a human label for a stable key (e.g. a country code)
    without exposing the raw key when a label exists.
    """
    if mapping is None:
        return key
    try:
        return mapping.get(key, key)
    except AttributeError:
        return key
