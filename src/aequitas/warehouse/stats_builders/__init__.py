"""Stats builder modules — one per template-contract family.

Each module exposes functions that build the `stats` dict for one or more
section_ids, matching the exact key contract their Jinja2 template expects.
precompute.py dispatches to these via _SECTION_BUILDERS.
"""
