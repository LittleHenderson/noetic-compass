import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def load_story(name: str) -> dict:
    with open(os.path.join(ROOT, "fixtures", name), "r",
              encoding="utf-8") as fh:
        return json.load(fh)


def good_story() -> dict:
    return load_story("story_good.json")


def broken_story(mutation) -> dict:
    story = copy.deepcopy(load_story("story_good.json"))
    mutation(story)
    return story
