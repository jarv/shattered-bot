"""Fill free accessory slots; keep artifact activation and swaps conservative."""
import re

try:
    from .combat_items import stats, known_cursed, ring_score, accessory_kind, empty_ring_candidate
except ImportError:
    from combat_items import stats, known_cursed, ring_score, accessory_kind, empty_ring_candidate


# Explicit supported loadout; dangerous/quest-dependent artifacts are not guessed.
ARTIFACT_PRIORITY = {
    "ethereal chains": 10, "timekeeper's hourglass": 9, "cloak of shadows": 9,
    "horn of plenty": 8, "alchemist's toolkit": 8, "talisman of foresight": 6,
    "chalice of blood": 5, "cape of thorns": 3,
    "lloyd's beacon": 7,
    "sandals of nature": 6, "shoes of nature": 6, "boots of nature": 6, "greaves of nature": 6,
    "master thieves' armband": 7,
    "dried rose": 5, "unstable spellbook": 6,
    "holy tome": 7, "skeleton key": 8,
}

ARTIFACT_STRATEGIES = {
    'ethereal chains':'Prioritize visible grounded-enemy chasm pulls; otherwise verified anchored escape',
    "timekeeper's hourglass":'Time freeze for dangerous combat; validate activation UI',
    'cloak of shadows':'Observed stealth for critical withdrawal',
    'horn of plenty':'Starvation relief or bounded meal/recharge use',
    "alchemist's toolkit":'Known-recipe alchemy through the ordinary observed crafting UI',
    'talisman of foresight':'Bounded observed-target scry; trap fields are a priority',
    'chalice of blood':'Inspect prick damage; confirm only within the public HP reserve',
    'cape of thorns':'Passive retaliation; no invented activation',
    "lloyd's beacon":'Verified same-floor safe anchor/return, excluding boss floors',
    "master thieves' armband":'Adjacent enemy blind/cripple; never steal from shopkeepers',
    'dried rose':'Observed-strength empty-slot outfitting with verified safe spares; eligible summon and bounded direct orders',
    'unstable spellbook':'Add only identified scrolls named by current blank-page index while preserving reserves; verify consumption/book change; bounded reading',
    'holy tome':'Use publicly offered Holy Ward via labeled spell UI and verified charge/buff; no Mage class restriction assumed',
    'skeleton key':'Observed iron/chest unlocks and flight-aware safe doorway locking; verify outcome; never unlock boss exits',
}
for _name in ('sandals of nature','shoes of nature','boots of nature','greaves of nature'):
    ARTIFACT_STRATEGIES[_name]='Observed seed ability and bounded feeding; retain seed reserves'


def artifact_name(item):
    return re.sub(r" [+-]\d+(?: x\d+)?$", "", item["name"].lower())


def equip_artifact(p, state):
    equipped = [i for i in state["inventory"] if i.get("equipped") and accessory_kind(i)]
    artifacts = [i for i in equipped if accessory_kind(i)=='artifact']
    names = {artifact_name(i) for i in artifacts}
    candidates = [i for i in state["inventory"] if not i.get("equipped")
                  and "EQUIP" in i.get("actions", []) and artifact_name(i) in ARTIFACT_PRIORITY
                  and artifact_name(i) not in names and not known_cursed(i)
                  and (len(equipped)<3 and len(artifacts)<2 or i.get("identified") or i.get("curse_known"))]
    if candidates:
        item = max(candidates, key=lambda i: ARTIFACT_PRIORITY[artifact_name(i)])
        if len(equipped) >= 3 or len(artifacts) >= 2:
            replaceable = artifacts if len(artifacts) >= 2 else equipped
            replaceable = [i for i in replaceable if "UNEQUIP" in i.get("actions", []) and not known_cursed(i)
                           and (i.get("identified") or i.get("curse_known"))]
            def value(i):
                return ARTIFACT_PRIORITY.get(artifact_name(i), ring_score(i)*1.5)
            if not replaceable:
                return None
            worst = min(replaceable, key=value)
            if value(item) < value(worst)+3:
                return None
            p.artifact_swap = item["name"]
            return p.use(worst, "UNEQUIP", "artifact: remove lower-value known safe accessory before explicit swap")
        return p.use(item, "EQUIP", "artifact: fill empty slot unless artifact is known cursed")
    return None


def cleanse_accessory(p,state):
    if not any(i.get('equipped') and known_cursed(i) and accessory_kind(i) for i in state['inventory']):
        return None
    scroll=next((i for i in state['inventory'] if i['name'].lower().startswith('scroll of remove curse')
                 and 'READ' in i.get('actions',[])),None)
    if scroll:
        p.menu_plan='discover-scroll'
        p.consumable_menu_bags=set()
        return p.use(scroll,'READ','accessory: prioritize cleansing cursed worn ring/artifact')
    return None


def use_artifact(p, state, enemies):
    if getattr(p,'unit_strategies_enabled',False):
        try:
            from .artifact_extensions import observe,choose
        except ImportError:
            from artifact_extensions import observe,choose
        observe(p,state)
    hero = state["hero"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    equipped = {artifact_name(i): i for i in state["inventory"] if i.get("equipped") and not known_cursed(i)}
    if enemies and getattr(p,'unit_strategies_enabled',False):
        try:
            from .chain_tactics import choose_chasm_pull
        except ImportError:
            from chain_tactics import choose_chasm_pull
        pull=choose_chasm_pull(p,state,enemies,equipped.get('ethereal chains'))
        if pull:return pull
    if getattr(p,'unit_strategies_enabled',False):
        if not enemies:
            cleanse=cleanse_accessory(p,state)
            if cleanse:return cleanse
        extra=choose(p,state,enemies)
        if extra:return extra
    if not enemies:
        cleanse=cleanse_accessory(p,state)
        if cleanse:return cleanse
        if p.artifact_swap:
            item = next((i for i in state["inventory"] if i["name"] == p.artifact_swap and "EQUIP" in i.get("actions", [])), None)
            p.artifact_swap = None
            if item:
                return p.use(item, "EQUIP", "artifact: finish validated accessory swap")
        horn = equipped.get("horn of plenty")
        if horn and "starving" in buffs and "EAT" in horn.get("actions", []):
            return p.use(horn, "EAT", "artifact: horn satiety and Mage meal talents"+
                         (' despite On Diet' if getattr(p,'on_diet',False) else ''))
        if horn and "hungry" in buffs and "SNACK" in horn.get("actions", []) and not p.charged_magic(state) \
                and any(t["name"].lower() == "energizing meal" and t["points"] for t in hero.get("talents", [])):
            return p.use(horn, "SNACK", "artifact: one-charge meal activates Mage wand recharge")
        ring=empty_ring_candidate(state)
        if ring:return p.use(ring,'EQUIP','accessory: fill empty ring slot unless known cursed')
        passive = equip_artifact(p, state)
        if passive:
            return passive
        sandals = next((i for name, i in equipped.items() if name in {"sandals of nature", "shoes of nature", "boots of nature", "greaves of nature"}), None)
        if sandals:
            description = sandals.get("description", "").replace("_", "").lower()
            if "ROOT" in sandals.get("actions", []) and "seed of sungrass" in description \
                    and hero["hp"] < 0.75*hero["max_hp"] and "herbal healing" not in buffs and not p.artifact_cooldown:
                p.artifact_cooldown = 24
                return p.use(sandals, "ROOT", "artifact: invoke inspected sungrass ability directly; no seed planting", target=hero["cell"])
            if "FEED" in sandals.get("actions", []) and not p.artifact_cooldown:
                seeds = [i for i in state["inventory"] if i["name"].lower().startswith("seed of ")
                          and ("sungrass" in i["name"].lower() or i.get("quantity", 1) >= 4)
                          and not ("sungrass" in i["name"].lower() and hero['hp']<.8*hero['max_hp'])
                         and (sandals["name"], i["name"]) not in p.artifact_feed_attempts]
                if seeds:
                    seed = max(seeds, key=lambda i: ("sungrass" in i["name"].lower(), i.get("quantity", 1)))
                    p.artifact_feed_attempts.add((sandals["name"], seed["name"]))
                    p.artifact_menu = {"kind": "feed", "target": seed["name"].lower(), "bags": set(), "steps": 0}
                    p.artifact_cooldown = 8
                    return p.use(sandals, "FEED", "artifact: feed sungrass or surplus seed; retain three-seed brewing reserve")
        beacon = equipped.get("lloyd's beacon")
        if beacon and "SET" in beacon.get("actions", []) and state["depth"] % 5 != 0 \
                and p.beacon_anchor != (state["depth"], hero["cell"]) and p.beacon_floor != state["depth"]:
            p.beacon_anchor = (state["depth"], hero["cell"])
            p.beacon_floor = state["depth"]
            return p.use(beacon, "SET", "artifact: set observed safe same-floor return anchor")
        chalice = equipped.get("chalice of blood")
        if chalice and "PRICK" in chalice.get("actions", []) and not p.artifact_cooldown \
                and hero["hp"] >= 0.95*hero["max_hp"] and "hungry" not in buffs and "starving" not in buffs:
            p.artifact_cooldown = 40
            p.artifact_menu = "chalice"
            return p.use(chalice, "PRICK", "artifact: inspect rendered prick damage before deciding")
        talisman = equipped.get("talisman of foresight")
        # A rendered foresight warning is already evidence worth inspecting:
        # do not require failed wall searches before checking a loot approach.
        # This is information only, not a trap identity or a safe-route receipt.
        raw = (talisman.get("status") or "?").rstrip("%") if talisman else "?"
        if talisman and "SCRY" in talisman.get("actions", []) and "foresight" in buffs \
                and raw.isdigit() and int(raw) >= 20 \
                and sum(d == state["depth"] for d, _ in p.scry_attempts) < 2 \
                and state.get("status") == "ready" and not state.get("modal") \
                and not state.get("danger_cells") and not p.recent_threats \
                and not p.unseen_damage_turns \
                and not any(b in buffs for b in ("starving", "burn", "poison", "bleed",
                                                "blind", "vertigo", "paral", "root", "magic immun")) \
                and not (p.puzzle_probe or p.potion_stash or p.room_journey or p.drop_plan):
            width = state["map"]["width"]
            pos = hero["cell"]
            paths = p.paths(state)
            targets = []
            for cell, obj in p.loot.items():
                dist = max(abs(cell % width-pos % width), abs(cell//width-pos//width))
                if not (2 <= dist <= 4) or cell not in paths or obj.get("for_sale") \
                        or not obj.get("top_item") or not p.tiles[cell].get("visible") \
                        or (state["depth"], cell) in p.scry_attempts:
                    continue
                route = p.route(paths, cell)
                if len(route) > 5 or not p.shot_clear(state, cell) or any(
                        p.tiles[c].get("trap") or p.tiles[c].get("plant")
                        or p.effects_block_movement(p.tiles[c]) or c in p.room_blocked
                        or p.tiles[c]["terrain"] in {7,8,10,18,21,22,31,37,38}
                        for c in route):
                    continue
                targets.append((len(route), cell))
            if targets:
                _, target = min(targets)
                p.scry_attempts.add((state["depth"], target))
                return p.use(talisman, "SCRY",
                             "artifact: inspect foresight warning toward observed loot before walking",
                             target=target)
        try:
            from .hidden_doors import secret_search_allowed
        except ImportError:
            from hidden_doors import secret_search_allowed
        if talisman and "SCRY" in talisman.get("actions", []) and p.searches >= 4 and secret_search_allowed(state,p):
            width = state["map"]["width"]
            walls = [c for c, t in p.tiles.items() if t["terrain"] == 4 and t.get("visible")
                     and 2 <= max(abs(c % width-hero["cell"] % width), abs(c//width-hero["cell"]//width)) <= 4
                     and (state["depth"], c) not in p.scry_attempts]
            raw = (talisman.get("status") or "?").rstrip("%")
            if walls and raw.isdigit() and int(raw) >= 20 and sum(d == state["depth"] for d, _ in p.scry_attempts) < 2:
                target = min(walls)
                p.scry_attempts.add((state["depth"], target))
                return p.use(talisman, "SCRY", "artifact: bounded scry toward observed wall after unsuccessful searching", target=target)
        return None
    if hero["hp"] >= 0.65 * hero["max_hp"] or p.artifact_cooldown:
        return None
    armband = equipped.get("master thieves' armband")
    if armband and "STEAL" in armband.get("actions", []) and len(enemies) == 1 \
            and not any(s in buffs for s in ("invisib", "cloaked")):
        width = state["map"]["width"]
        target = enemies[0]
        if max(abs(target["cell"]%width-hero["cell"]%width), abs(target["cell"]//width-hero["cell"]//width)) == 1:
            p.artifact_cooldown = 12
            return p.use(armband, "STEAL", "artifact: blind and cripple observed adjacent enemy; never steal from shop", target=target["cell"])
    beacon = equipped.get("lloyd's beacon")
    if beacon and "RETURN" in beacon.get("actions", []) and p.beacon_anchor and p.beacon_anchor[0] == state["depth"] \
            and state["depth"] % 5 != 0 and p.tiles.get(p.beacon_anchor[1], {}).get("visible") \
            and p.walkable(p.beacon_anchor[1], {e["cell"] for e in enemies}):
        width = state["map"]["width"]
        dist = lambda a, b: max(abs(a % width-b % width), abs(a//width-b//width))
        if all(dist(hero["cell"], e["cell"]) > 1 and dist(p.beacon_anchor[1], e["cell"]) >= 4 for e in enemies):
            p.artifact_cooldown = 12
            return p.use(beacon, "RETURN", "artifact: return to verified visible same-floor anchor before encirclement")
    chains = equipped.get("ethereal chains")
    if chains and "CAST" in chains.get("actions", []) and "root" not in buffs:
        raw = (chains.get("status") or "?").split("/")[0]
        if raw.isdigit():
            width, height = state["map"]["width"], state["map"]["height"]
            def dist(a, b):
                return max(abs(a % width - b % width), abs(a // width - b // width))
            threats = [e for e in enemies if not e.get("sleeping")]
            current = min((dist(hero["cell"], e["cell"]) for e in threats), default=99)
            paths = p.paths(state, {o["cell"] for o in state.get("objects", [])})
            choices = []
            for cell in paths:
                tile = p.tiles[cell]
                if not tile.get("visible") or tile["terrain"] not in {1, 2, 3, 11, 14, 19, 20, 29} \
                        or tile.get("plant") or tile.get("trap") or tile.get("effects") \
                        or cell in state.get("danger_cells", []) or cell in p.loot \
                        or not 2 <= dist(hero["cell"], cell) <= min(4, int(raw)):
                    continue
                anchored = any(p.tiles.get(y*width+x, {}).get("terrain") == 4
                               for x in range(max(0, cell % width-1), min(width, cell % width+2))
                               for y in range(max(0, cell // width-1), min(height, cell // width+2)))
                separation = min((dist(cell, e["cell"]) for e in threats), default=0)
                if anchored and separation >= max(3, current+2) and p.shot_clear(state, cell):
                    choices.append((separation, -dist(hero["cell"], cell), cell))
            if choices:
                p.artifact_cooldown = 12
                return p.use(chains, "CAST", "artifact: chain to visible anchored escape; preserve return route",
                             target=max(choices)[2])
    cloak = equipped.get("cloak of shadows")
    if cloak and not any(s in buffs for s in ("invisib", "stealth", "cloaked")) and "STEALTH" in cloak.get("actions", []):
        p.artifact_cooldown = 12
        return p.use(cloak, "STEALTH", "artifact: cloak for critical-health withdrawal")
    hourglass = equipped.get("timekeeper's hourglass")
    if hourglass and "time freeze" not in buffs and "time stasis" not in buffs and "ACTIVATE" in hourglass.get("actions", []):
        p.artifact_cooldown = 12
        p.artifact_menu = "freeze"
        return p.use(hourglass, "ACTIVATE", "artifact: freeze time rather than spend HP in melee")
    return None
