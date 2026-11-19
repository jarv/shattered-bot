"""English inspection-text estimates, never hidden item levels or curse flags."""
import re


def text(item):
    return item.get("description", "").replace("_", "").lower()


def known_cursed(item):
    return item.get("known_cursed", False)


ARTIFACT_NAMES = {
    "ethereal chains", "timekeeper's hourglass", "cloak of shadows", "horn of plenty",
    "alchemist's toolkit", "talisman of foresight", "chalice of blood", "cape of thorns",
    "lloyd's beacon", "sandals of nature", "shoes of nature", "boots of nature",
    "greaves of nature", "master thieves' armband", "dried rose", "unstable spellbook",
    "holy tome", "skeleton key",
}


def accessory_kind(item):
    """Recognize public accessory names, not hidden identities or generic gear."""
    name=re.sub(r" [+-]\d+(?: x\d+)?$", "", item["name"].lower())
    if name.startswith("ring of ") or name.endswith(" ring"):
        return "ring"
    if name in ARTIFACT_NAMES:return "artifact"
    return None


def empty_ring_candidate(state):
    worn=[i for i in state['inventory'] if i.get('equipped') and accessory_kind(i)]
    if len(worn)>=3 or sum(accessory_kind(i)=='ring' for i in worn)>=2:return None
    rings=[i for i in state['inventory'] if not i.get('equipped') and accessory_kind(i)=='ring'
           and 'EQUIP' in i.get('actions',[]) and not known_cursed(i)]
    return max(rings,key=ring_score) if rings else None


def unencumbered(state):
    """Do not promise timed movement using unknown or over-strength armor."""
    armor = [i for i in state["inventory"] if i.get("equipped") and (
        stats(i) and stats(i)[0] == "armor" or "IMBUE" not in i.get("actions", [])
        and any(k in i["name"].lower() for k in ("armor", "robe")))]
    return all(i.get("identified") and stats(i) and stats(i)[0] == "armor"
               and stats(i)[2] <= state["hero"]["strength"] for i in armor)


def stats(item):
    description = text(item)
    match = re.search(r"(melee weapon deals|thrown weapons deals|armor blocks) (\d+)-(\d+) damage and requires (\d+) strength", description)
    if not match:
        return None
    kind = {"melee weapon deals": "melee", "thrown weapons deals": "thrown", "armor blocks": "armor"}[match[1]]
    return kind, (int(match[2]) + int(match[3])) / 2, int(match[4])


def physical_score(item, strength):
    value = stats(item)
    if not value or value[2] > strength or known_cursed(item):
        return 0
    kind, damage, requirement = value
    if kind == "armor":
        return damage
    damage += max(0, strength - requirement) / 2
    description = text(item)
    delay = 0.5 if "very fast weapon" in description else 0.8 if "rather fast weapon" in description else 1.5 if "rather slow weapon" in description else 1
    accuracy = 0.7 if "rather inaccurate" in description else 1.1 if "rather accurate" in description else 1
    return damage * accuracy / delay


def equipment_upgrade(state):
    inventory = state["inventory"]
    strength = state["hero"].get("strength", 0)
    for kind in ("armor", "melee"):
        current = next((i for i in inventory if i.get("equipped") and stats(i) and stats(i)[0] == kind), None)
        if current and known_cursed(current):
            continue  # Cannot replace cursed equipped gear through normal equip.
        baseline = physical_score(current, strength) if current else 0
        candidates = [i for i in inventory if "EQUIP" in i.get("actions", [])
                      and not i.get("equipped") and stats(i) and stats(i)[0] == kind
                      and physical_score(i, strength) > baseline
                      # A tiny apparent weapon gain isn't worth discovering a
                      # binding curse. Armor upgrades remain urgent early on.
                      and (kind != "melee" or i.get("curse_known") or i.get("identified")
                           or physical_score(i, strength) >= max(baseline * 1.25, baseline + 2))]
        if candidates:
            return max(candidates, key=lambda i: physical_score(i, strength))
    return empty_ring_candidate(state)


def ring_score(item):
    if not item.get("identified") or known_cursed(item):
        return 0
    weights = {"energy": 6, "haste": 5, "evasion": 4, "might": 4, "furor": 3,
               "sharpshooting": 3, "accuracy": 2, "tenacity": 2, "wealth": 1, "arcana": 1}
    name = item["name"].lower()
    weight = next((v for kind, v in weights.items() if f"ring of {kind}" in name), 0)
    match = re.search(r"([+-]\d+)(?:\s|$)", name)
    level = int(match[1]) if match else 0
    return weight * max(0, level+1)


def magic_score(item):
    if known_cursed(item) or "ZAP" not in item.get("actions", []):
        return 0
    charge = (item.get("status") or "?").split("/")[0]
    if charge.isdigit() and int(charge) == 0:
        return 0
    # Exclude area/gas/cone/chain and non-damage wands until their geometry is modeled.
    if not any(name in item["name"].lower() for name in
               ("magic missile", "frost", "disintegration", "prismatic light", "living earth")):
        return 0
    matches = list(re.finditer(r"(\d+)-(\d+) damage", text(item)))
    match = matches[-1] if matches else None  # Staff inspection lists melee first, wand last.
    # Legacy observation fixtures have no description; real observations always do.
    return (int(match[1]) + int(match[2])) / 2 if match else 4 if "description" not in item else 0
