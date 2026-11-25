import unittest

from tools.mage_policy import MagePolicy
from tools import test_ghost_return_and_spellbook_add as fixtures
from tools.artifact_extensions import choose
from tools.spellbook_feeding import menu, observe


class SimpleSpellbookTests(unittest.TestCase):
    def setup_book(self, name="scroll of rage", quantity=1):
        s, _, book, scroll = fixtures.SpellbookAddTests().setup_book(name, quantity)
        p = MagePolicy(profile="simple-bot")
        p.challenges_verified = True
        p.update(s)
        return s, p, book, scroll

    def test_simple_artifact_pipeline_adds_requested_identified_scroll_before_random_reading(self):
        s, p, book, _ = self.setup_book()
        action = choose(p, s, [])
        self.assertEqual("ADD", action.action["action"])
        self.assertFalse(p.profile.special_rooms)
        self.assertEqual("spellbook-add", p.artifact_menu["kind"])

    def test_simple_add_selector_requires_consumption_and_public_book_change(self):
        s, p, book, scroll = self.setup_book()
        choose(p, s, [])
        s["ui"] = {"texts": ["Select a scroll"],
                   "buttons": [{"id": "feed-rage", "label": "scroll of rage"}]}
        self.assertEqual("feed-rage", menu(p, s, p.artifact_menu).action["id"])
        self.assertNotIn("spellbook_add", p.planner.report)
        s["inventory"].remove(scroll)
        book["name"] = "unstable spellbook +1"
        observe(p, s)
        self.assertTrue(p.planner.report["spellbook_add"]["confirmed"])

    def test_simple_preserves_last_identify_and_rejects_unknown_or_unrequested_scrolls(self):
        for name, quantity, identified, expected in (
                ("scroll of identify", 1, True, False),
                ("scroll of identify", 2, True, True),
                ("scroll of rage", 1, False, False),
                ("scroll of teleportation", 2, True, False)):
            s, p, book, scroll = self.setup_book(name, quantity)
            scroll["identified"] = identified
            action = choose(p, s, [])
            self.assertEqual(expected, action is not None and action.action.get("action") == "ADD", name)
