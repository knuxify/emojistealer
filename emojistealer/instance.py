# SPDX-License-Identifier: MIT
"""
Instance types and relevant parsing/download functions.
"""

from . import logger
from .emoji import Emoji
from .request import request_get, RequestError

from functools import cached_property
from urllib.parse import urljoin, urlparse
from typing import List, Self, Union


def get_base_url(url: str) -> str:
    """
    Clean up a link and extract the scheme and domain from it.

    :raises ValueError: if the URL is malformed.
    """
    url_parsed = urlparse(url)

    scheme = "https"
    if url_parsed.scheme:
        scheme = url_parsed.scheme
        if scheme not in ("http", "https"):
            raise ValueError(f"Not an HTTP/HTTPS URL: {url}")

    if url_parsed.netloc:
        domain = url_parsed.netloc
    elif url_parsed.path:
        domain = url_parsed.path.strip().split("/")[0]
    else:
        raise ValueError(f"Malformed URL: {url}")

    return f"{scheme}://{domain}"


class Instance:
    """
    Represents a Fediverse instance. Subclasses of this class represent specific
    server software (Mastodon, Pleroma/Akkoma, Misskey etc).
    """

    def __init__(self, url: str):
        """
        Initialize the Instance object.

        :params url: URL of the instance.
        """
        #: Base URL of the instance, with the https prefix.
        self.url = get_base_url(url)

    @classmethod
    def create_for_url(cls, url: str) -> Self:
        """
        Create an Instance object, auto-detecting the type.

        :raises ValueError: if the instance is unsupported.
        """
        _url = get_base_url(url)

        for instance_type in cls.instance_types:
            if instance_type.matches_url(_url):
                return instance_type(_url)

        raise ValueError(f"Cannot identify instance type for {_url}")


class InstanceMastodon(Instance):
    """
    Represents a Mastodon instance.
    """

    __software__ = "Mastodon"

    @classmethod
    def matches_url(cls, url: str) -> bool:
        """
        Check if the instance with the provided URL is of this type.

        :param url: URL of the instance to check for.
        """
        return True  # TODO: Add "Mastodon-like" type

    # Sort-of-hack: self type is typed this way to allow fallback to MastoAPI
    # from InstancePleroma object without duplicating the code
    @cached_property
    def all_emoji(self: Union[Self, "InstancePleroma"]) -> List[Emoji]:
        """
        Get the emoji of this instance as an EmojiList.
        """
        emoji_list = []

        try:
            req = request_get(
                urljoin(self.url, "/api/v1/custom_emojis"), parse_json=True
            )
        except RequestError:
            return emoji_list

        for emoji in req:
            if not emoji.get("shortcode", ""):
                logger.warn(f"Missing shortcode for emoji")
                continue

            if not emoji.get("url", "") and not emoji.get("static_url", ""):
                logger.warn(f"Missing URL for emoji {emoji['shortcode']}")
                continue

            emoji_list.append(
                Emoji(
                    shortcode=emoji["shortcode"],
                    category=InstancePleroma._category_fixup(emoji.get("category")),
                    original_url=emoji.get("url", ""),
                    static_url=emoji.get("static_url", ""),
                )
            )

        return emoji_list


class InstancePleroma(Instance):
    """
    Represents a Pleroma/Akkoma instance.
    """

    __software__ = "Pleroma"

    def __init__(self, url: str):
        super().__init__(url)

        try:
            req = request_get(urljoin(self.url, "/api/v1/instance"), parse_json=True)
        except RequestError:
            pass
        else:
            is_akkoma = False
            try:
                is_akkoma = "akkoma_api" in req["pleroma"]["metadata"]["features"]
            except KeyError:
                pass

        if is_akkoma:
            self.__software__ = "Akkoma"

    @classmethod
    def matches_url(cls, url: str) -> bool:
        """
        Check if the instance with the provided URL is of this type.

        :param url: URL of the instance to check for.
        """
        try:
            req = request_get(
                urljoin(get_base_url(url), "/api/v1/instance"), parse_json=True
            )
        except RequestError:
            return False
        return "pleroma" in req

    @cached_property
    def all_emoji(self) -> List[Emoji]:
        """
        Get the emoji of this instance as an EmojiList.
        """
        emoji_list = []

        try:
            req = request_get(
                urljoin(self.url, "/api/v1/pleroma/emoji"), parse_json=True
            )
        except RequestError:
            # If the pleroma emoji API is missing (TODO - is this possible?),
            # fall back to Mastodon-style emoji API.
            return InstanceMastodon.all_emoji(self, drop_pack_prefix=True)

        for shortcode, emoji in req.items():
            if not emoji.get("image_url", ""):
                logger.warn(f"Missing URL for emoji {shortcode}")
                continue

            category = None
            for tag in emoji.get("tags"):
                if tag.startswith("pack:"):
                    category = tag[5:]
                    break

            # If URL is not prefixed with instance domain, do it manually
            url = emoji["image_url"]
            if not url.startswith("http://") or url.startswith("https://"):
                url = urljoin(self.url, url)

            emoji_list.append(
                Emoji(
                    shortcode=shortcode,
                    category=category,
                    original_url=url,
                    static_url=url,
                )
            )

        return emoji_list

    @classmethod
    def _category_fixup(cls, category: str):
        """Strip "pack:" prefix from Pleroma emoji category/tag names."""
        if not category:
            return None
        if category.startswith("pack:"):
            return category[5:]
        return category


class InstanceMisskey(Instance):
    """
    Represents a Misskey instance.
    """

    __software__ = "Misskey"

    @classmethod
    def matches_url(cls, url: str) -> bool:
        """
        Check if the instance with the provided URL is of this type.

        :param url: URL of the instance to check for.
        """
        # TODO better check
        try:
            req = request_get(
                urljoin(get_base_url(url), "/api/v1/instance"), parse_json=True
            )
        except RequestError as e:
            e = int(str(e))
            if e == 404:
                return True

        return False

    @cached_property
    def all_emoji(self) -> List[Emoji]:
        """
        Get the emoji of this instance as an EmojiList.
        """
        emoji_list = []

        try:
            req = request_get(urljoin(self.url, "/api/emojis"), parse_json=True)
        except RequestError:
            return emoji_list

        for emoji in req.get("emojis", []):
            if not emoji.get("name", ""):
                logger.warn(f"Missing shortcode for emoji")
                continue

            if not emoji.get("url", ""):
                logger.warn(f"Missing URL for emoji {emoji['shortcode']}")
                continue

            emoji_list.append(
                Emoji(
                    shortcode=emoji["name"],
                    category=emoji["category"] or None,
                    original_url=emoji["url"],
                    static_url=emoji["url"],
                )
            )

        return emoji_list


Instance.instance_types = [InstancePleroma, InstanceMisskey, InstanceMastodon]
