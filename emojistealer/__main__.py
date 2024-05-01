# SPDX-License-Identifier: MIT

from . import VERSION, logger
from .utils import colors
from .request import request_download, RequestError
from .instance import Instance

import argparse
import os.path
import json

parser = argparse.ArgumentParser(
    prog="emojistealer",
    description="Download emoji from Mastodon/Pleroma/Misskey instances",
)

parser.add_argument("url", help="URL of the instance to download emoji from")
parser.add_argument(
    "--original",
    action='store_true',
    help='download emoji from "original URL" instead of "static URL" (only for Mastodon, does not make a difference on Pleroma/Misskey',
)
parser.add_argument("-o", "--output", help="output directory to save the emoji to", default="./emoji-downloads")

args = parser.parse_args()
url = args.url
output_dir = args.output

logger.info(f"{colors['bold']}emojistealer{colors['reset']} {VERSION}")
logger.info("===\n")
logger.info(
    f"Attempting to find instance information for {colors['bold']}{url}{colors['reset']}..."
)

instance = Instance.create_for_url(url)

if not instance:
    logger.error("Could not identify type of instance.")
    quit(1)

logger.info(
    f"Found {colors['bold']}{instance.__software__}{colors['reset']} instance: {colors['bold']}{instance.url}{colors['reset']}\n"
)

logger.info(f"Getting emoji list...")
all_emoji = instance.all_emoji
all_emoji_shortcodes = dict([(e.shortcode, e) for e in all_emoji])

if not all_emoji:
    logger.error(
        f"No emoji found! Either this instance does not have any custom emoji, or it is denying our requests."
    )
    quit(1)

emoji_categorized = {}
for emoji in all_emoji:
    category = emoji.category or "(uncategorized)"
    if category in emoji_categorized:
        emoji_categorized[category].append(emoji)
    else:
        emoji_categorized[category] = [emoji]

logger.info(f"Available emoji:\n")
for category, category_emoji in sorted(emoji_categorized.items()):
    logger.info(f"{colors['bold']}{category}{colors['reset']}:")
    logger.info(" " + " ".join([e.shortcode for e in category_emoji]))

logger.info("\n")

logger.info("Select emoji to download:")
logger.info(" <name> or emoji:<name> - selects an emoji")
logger.info(" pack:<name> - selects an entire category")
logger.info(" unselect <name> or unselect pack:<name> - unselects an emoji/pack")
logger.info(" all - selects all emoji")
logger.info(" none - unselects all emoji")
logger.info(" confirm - confirms your selection")
logger.info(" quit - quits the program")

selected = {}

while True:
    while True:
        _query = input("> ")
        query = _query.split(" ")
        if not query:
            continue

        if len(query) > 1:
            for command in ("all", "none", "confirm", "quit"):
                if command in query:
                    logger.warn(
                        "all, none, confirm are ignored if other emoji/packs are provided. Please input them separately."
                    )
                    while command in query:
                        query.remove(command)
            if query[0] == "unselect":
                for shortcode in query[1:]:
                    if shortcode.startswith("pack:"):
                        for pack_sc in [
                            e.shortcode for e in emoji_categorized[shortcode[5:]]
                        ]:
                            try:
                                del selected[pack_sc]
                            except KeyError:
                                pass
                    else:
                        try:
                            del selected[shortcode]
                        except KeyError:
                            logger.warn(f"Not selected: {shortcode}, ignoring")
            else:
                for shortcode in query:
                    if shortcode.startswith("pack:"):
                        for emoji in emoji_categorized[shortcode[5:]]:
                            selected[emoji.shortcode] = emoji
                    else:
                        if shortcode.startswith("emoji:"):
                            shortcode = shortcode[6:]
                        try:
                            selected[shortcode] = all_emoji_shortcodes[shortcode]
                        except KeyError:
                            logger.warn(f"No such emoji: {shortcode}, ignoring")
        else:
            if query[0] == "confirm":
                break
            elif query[0] == "all":
                selected = dict([(e.shortcode, e) for e in all_emoji])
            elif query[0] == "none":
                selected = {}
            elif query[0] == "quit":
                quit(0)
            else:
                shortcode = query[0]
                if shortcode.startswith("pack:"):
                    for emoji in emoji_categorized[shortcode[5:]]:
                        selected[emoji.shortcode] = emoji
                else:
                    if shortcode.startswith("emoji:"):
                        shortcode = shortcode[6:]
                    try:
                        selected[shortcode] = all_emoji_shortcodes[shortcode]
                    except KeyError:
                        logger.warn(f"No such emoji: {shortcode}, ignoring")

        logger.info(f"{len(selected)} emoji selected.")

    logger.info("\nYour selection:")
    logger.info(" ".join(list(selected.keys())))
    yn = input("\nIs this correct? [Y]/N > ")
    if not yn or yn in ("y", "Y"):
        break

logger.info("Downloading emoji...")

h = None
for handler in logger.handlers:
    if handler.name == "my_handler":
        h = handler

packs = {}

for emoji in selected.values():
    h.terminator = ""
    logger.info(f"{emoji.shortcode}...")
    h.terminator = "\n"

    if args.original:
        url = emoji.original_url or emoji.static_url
    else:
        url = emoji.static_url or emoji.original_url

    emoji_filename = emoji.shortcode + os.path.splitext(url)[1]
    target_path = os.path.join(
                output_dir,
                emoji.category if emoji.category else "",
                emoji_filename,
            )

    if emoji.category in packs:
        packs[emoji.category]["files"][emoji.shortcode] = emoji_filename
    else:
        packs[emoji.category] = {}
        packs[emoji.category]["files"] = {emoji.shortcode: emoji.pack["pack"]}
        if emoji.pack and "pack" in emoji.pack and emoji.pack["pack"]:
            packs[emoji.category]["pack"] = emoji.pack["pack"]
        else:
            packs[emoji.category]["pack"] = {
                "description": pack_name,
                "homepage": instance.url,
                "share-files": True,
            }

    if os.path.exists(target_path):
        print(" already downloaded")
        continue

    try:
        request_download(
            url, target_path
        )
    except RequestError as e:
        print(" ✗")
        logger.warn(f"Server returned error: {int(str(e))}")
        continue
    else:
        print(" ✓")

logger.info("Writing pack.json files...")
for pack_name, pack_data in packs.items():
    with open(os.path.join(output_dir, pack_name, "pack.json"), "w") as f:
        json.dump(pack_data, f)

logger.info("Done! Enjoy your emoji!")

quit(0)
