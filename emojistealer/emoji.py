# SPDX-License-Identifier: MIT
"""Code for emoji parsing."""

from dataclasses import dataclass


@dataclass
class Emoji:
    """Class representing a single emoji."""

    #: The emoji shortcode for this emoji.
    shortcode: str

    #: URL to the original emoji. For Pleroma/Misskey, this is the same as
    #: static_url.
    original_url: str

    #: URL to the statically-served emoji. For Pleroma/Misskey, this is
    #: the same as original_url.
    static_url: str

    #: Category/pack that this emoji belongs to.
    category: str
