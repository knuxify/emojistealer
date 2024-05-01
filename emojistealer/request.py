# SPDX-License-Identifier: MIT
"""Wrapper for making requests"""

from . import VERSION, logger

import requests
from pyrate_limiter import Duration, RequestRate, Limiter
from requests import Session
from requests_cache import CacheMixin
from requests_ratelimiter import LimiterSession, LimiterMixin
from os import PathLike
import os.path
from pathlib import Path


class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    """Requests session that combines caching and ratelimiting."""


limiter = Limiter(RequestRate(10, Duration.SECOND * 3))

req_session = CachedLimiterSession("emojistealer_cache", expire_after=180, limiter=limiter)
req_nocache_session = LimiterSession(limiter=limiter)

HEADERS = {
    "User-Agent": "emojistealer {VERSION} (https://github.com/knuxify/emojistealer)"
}


class RequestError(Exception):
    """Base class for request exceptions."""


def request_get(url: str, parse_json: bool = False, no_cache: bool = False):
    session = req_session
    if no_cache:
        session = req_nocache_session

    req = session.get(
        url,
        headers=HEADERS,
    )
    if req.status_code != 200:
        logger.warn(f"Request error for {url}: {req.status_code}")
        logger.warn("Server response:\n" + req.text)
        raise RequestError(req.status_code)

    if parse_json:
        return req.json()

    return req.text


def request_download(url: str, target: PathLike):
    """Downloads a file to the given target location."""
    basedir = Path(os.path.dirname(target))
    if basedir.is_file():
        raise ValueError("Base directory already exists and is a file")

    if not basedir.is_dir():
        basedir.mkdir(parents=True)

    try:
        with req_nocache_session.get(url, headers=HEADERS, stream=True) as r:
            r.raise_for_status()
            with open(target, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.exceptions.HTTPError as e:
        raise RequestError(e.status_code)
