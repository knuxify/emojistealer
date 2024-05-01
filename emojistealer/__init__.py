# SPDX-License-Identifier: MIT
"""
emojistealer - Download emoji from Mastodon/Pleroma/Misskey instances and organize them
"""

import logging

VERSION = "0.1.0"

# Logger configuration


class LogFormatter(logging.Formatter):
    # https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
    FORMATS = {
        logging.DEBUG: "%(message)s",
        logging.INFO: "%(message)s",
        logging.WARN: "\x1b[33;20m[%(asctime)s] %(levelname)s: %(message)s\x1b[0m",
        logging.ERROR: "\x1b[31;20m[%(asctime)s] %(levelname)s: %(message)s\x1b[0m",
        logging.CRITICAL: "\x1b[31;1m[%(asctime)s] %(levelname)s: %(message)s\x1b[0m",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, "%(message)s")
        return logging.Formatter(log_fmt).format(record)


logger = logging.getLogger("emojistealer")
logger.setLevel(logging.INFO)

_log_stream = logging.StreamHandler()
_log_stream.setFormatter(LogFormatter())
_log_stream.setLevel(logging.INFO)
_log_stream.name = "my_handler"

logger.addHandler(_log_stream)
