"""Mage upgrade allocation from visible levels and strength breakpoints.

This is a survival heuristic, not a proof of a globally optimal build.
"""
import math
import re

try:
    from .combat_items import stats, known_cursed, physical_score, magic_score, ring_score
except ImportError:
    from combat_items import stats, known_cursed, physical_score, magic_score, ring_score


def visible_level(item):
    if not item.get("identified", False) and "typically" in item.get("description", "").lower():
        return None
    match = re.search(r"([+-]\d+)(?:\s|$)", item["name"])
    return int(match[1]) if match else 0


def strength_reduction(level):
    return int((math.sqrt(8 * max(0, level) + 1) - 1) / 2)


def supporting_upgrade(state, staff):
    inventory = state["inventory"]
    def nominal(item):
        return magic_score(dict(item, actions=["ZAP"], status="1/1"))
    wands = [i for i in inventory if "wand of " in i["name"].lower() and not known_cursed(i) and nominal(i) > 0]
    choices = []
    for item in inventory:
        if not item.get("identified") or known_cursed(item) or not item.get("upgradable", True):
            continue
        level = visible_level(item)
        if level is None or level < 0 or level >= 3:
            continue
        name = item["name"].lower()
        if item.get("equipped") and ring_score(item) > 0 and level < 2:
            weight = 0
            if "ring of energy" in name and wands:
                weight = 3  # Faster replenishment across staff and spare wands.
            elif "ring of haste" in name:
                weight = 3.5
            elif "ring of might" in name and any(stats(i) and stats(i)[2] == state["hero"].get("strength", 0)+1 for i in inventory):
                weight = 4
            elif "ring of evasion" in name:
                weight = 2.5
            elif "ring of sharpshooting" in name and any(stats(i) and stats(i)[0] == "thrown" and physical_score(i, state["hero"].get("strength", 0)) > 0 for i in inventory):
                weight = 2.5
            if weight:
                choices.append((weight, item, "useful equipped ring improves recharge, mobility, defense, or equipment access"))
        if item in wands:
            delta = next((gain for kind, gain in (("frost", 3), ("disintegration", 2.5), ("prismatic light", 2), ("living earth", 1.5), ("magic missile", 1.5)) if kind in name), 0)
            if delta and nominal(item)+delta >= nominal(staff)+1.5:
                choices.append((delta, item, "identified spare wand has a better damage-scaling investment"))
    if choices:
        _, item, reason = max(choices, key=lambda c: c[0])
        return item, reason
    return None


def choose_upgrade(state):
    inventory = state["inventory"]
    staff = next((i for i in inventory if "staff" in i["name"].lower() and "IMBUE" in i.get("actions", [])), None)
    if not staff or known_cursed(staff) or not staff.get("upgradable", True):
        return None
    staff_level = visible_level(staff) or 0
    if staff_level < 1:
        return staff, "first staff upgrade improves damage/charges and preserves one level on later imbue"
    strength = state["hero"].get("strength", 0)
    current = next((i for i in inventory if i.get("equipped") and stats(i) and stats(i)[0] == "armor"), None)
    current_block = physical_score(current, strength) if current else 0
    armor = []
    for item in inventory:
        value = stats(item)
        tier_match = re.search(r"tier[- ](\d+)", item.get("description", "").replace("_", "").lower())
        level = visible_level(item)
        if not value or value[0] != "armor" or not item.get("identified") or known_cursed(item) or level is None or not tier_match or not item.get("upgradable", True):
            continue
        if state.get("policy_rules", {}).get("faith_is_my_armor"):
            continue  # Normal tier-based blocking gains do not apply.
        tier = int(tier_match[1])
        after_requirement = value[2] - (strength_reduction(level+1) - strength_reduction(level))
        after_block = value[1] + (tier+1)/2
        unlock = value[2] > strength >= after_requirement
        durable = tier >= 3 and level < 3 and staff_level >= 3
        emergency_leather = tier == 2 and unlock and state["hero"]["hp"] < 0.6 * state["hero"]["max_hp"]
        if after_requirement <= strength and after_block - current_block >= 2 and (tier >= 3 and unlock or durable or emergency_leather):
            armor.append((after_block - current_block, item))
    if armor:
        return max(armor, key=lambda choice: choice[0])[1], "defensive armor upgrade or immediate strength breakpoint"
    if staff_level < 3:
        return staff, "reliable early-game staff damage and charge capacity"
    supporting = supporting_upgrade(state, staff)
    if supporting:
        return supporting
    scrolls = sum(i.get("quantity", 1) for i in inventory if "scroll of upgrade" in i["name"].lower())
    # Retain one flexible scroll after the early staff target instead of dumping
    # the entire run into a starting weapon while wearing cloth in the prison.
    if scrolls <= 1:
        return None
    return staff, "spend surplus while retaining one flexible upgrade"
