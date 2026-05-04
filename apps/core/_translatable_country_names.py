"""Anchor file: declare the country name strings for ``makemessages``.

``apps.core.views`` translates the MVP country names at runtime via
``_(ctx["country_name_key"])``. Because the argument is a string variable,
``makemessages`` cannot extract those names from the call site — without
the explicit ``_()`` calls below it would mark the entries obsolete in
the locale catalogues, which silently breaks IT/FR/AR rendering of the
``/countries/`` page (see ``test_country_names_translated_per_language``).

``gettext_noop`` registers the msgid in ``django.po`` without performing
the translation at module import (the actual lookup happens later in
``views._render_country_landing``). The list below must match
``MVP_COUNTRIES`` in ``apps/core/views.py``.
"""

from django.utils.translation import gettext_noop as _

_("Italy")
_("France")
_("Belgium")
_("Morocco")
_("Tunisia")
