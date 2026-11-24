"""Mage talent activations; never sacrifice the last usable offensive charge."""

try:
    from .consumable_tactics import base_name
    from .combat_items import magic_score
except ImportError:
    from consumable_tactics import base_name
    from combat_items import magic_score


def prepare_mask(p, state, enemies):
    """Owned progression, not optional crafting; keep safety/return admission."""
    try:
        from .survival_policy import is_hostile
    except ImportError:
        from survival_policy import is_hostile
    hero=state.get("hero",{})
    pos=hero.get("cell")
    tile=p.tiles.get(pos,{})
    if state.get("scene")!="GameScene" or state.get("status")!="ready" or state.get("modal") \
            or enemies or any(is_hostile(o) for o in state.get("objects",[])) \
            or p.recent_threats or p.unseen_damage_turns or state.get("danger_cells") \
            or state.get("boss_health_text") or hero.get("hp",0)<max(3,.3*hero.get("max_hp",0)):
        return None  # Preserve the quiet-state emergency-healing threshold.
    if any(getattr(p,name,None) for name in (
            "mage_plan","room_journey","puzzle_probe","potion_stash","trap_payload_return",
            "drop_plan","escape_commitment","ranged_plan","ambush_plan","doorway_hold",
            "well_cleanse_plan","food_freeze_plan")):
        return None
    buffs=" ".join(b["name"].lower() for b in hero.get("buffs",[]))
    if any(name in buffs for name in (
            "burn","poison","bleed","ooze","paral","vertigo","root","blind","chill",
            "frozen","drowsy","sleep","levitat","invisib","cloaked")):
        return None
    if not tile.get("visible") or not tile.get("observed",tile.get("visible",False)) \
            or tile.get("terrain") not in {1,2,3,6,7,8,9,11,14,15,19,20,22,29,30} \
            or any(tile.get(k) for k in ("effects","trap","plant")) \
            or pos in p.room_blocked or not p.escape_step_allowed(state,pos):
        return None
    if hero.get("subclass","").lower() in {"warlock","battlemage"}:
        return None
    item=next((i for i in state.get("inventory",[]) if base_name(i)=="tengu's mask"
               and "WEAR" in i.get("actions",[]) and p.item_action_allowed(i,"WEAR")),None)
    if item:
        p.mage_plan={"kind":"choice","choice":"warlock","stage":"select","steps":0}
        return p.use(item,"WEAR","mage: choose warlock before optional exploration or descent")


def prepare_mage(p, state):
    """Explicit subclass/armor choices and preservation-confirmed staff imbues."""
    mask=prepare_mask(p,state,[])
    if mask:
        return mask
    inventory = state["inventory"]
    armor = next((i for i in inventory if i.get("equipped") and "ABILITY" in i.get("actions", [])), None)
    anchor = (state["depth"], state.get("branch", 0), state["hero"]["cell"])
    if armor and p.mage_plan and p.mage_plan["kind"] == "warp":
        if p.mage_plan["stage"] == "set_after_clear":
            p.mage_plan["stage"] = "await_set"
            return p.use(armor, "ABILITY", "mage: place same-floor warp beacon on observed safe tile", target=anchor[2])
        if p.mage_plan["stage"] == "await_set":
            p.warp_anchor = p.mage_plan["anchor"]
            p.mage_plan = None
    if armor and state["hero"].get("armor_ability", "").lower() == "warp beacon" \
            and state["depth"] % 5 != 0 and p.warp_setup_floor != state["depth"]:
        raw = (armor.get("status") or "?").rstrip("%")
        if raw.isdigit() and int(raw) >= 35:
            p.warp_setup_floor = state["depth"]
            p.mage_plan = {"kind": "warp", "stage": "clear" if p.warp_anchor else "await_set", "anchor": anchor, "steps": 0}
            return p.use(armor, "ABILITY", "mage: establish verified same-floor warp return plan", target=anchor[2])
    for name, choice in (("dwarf king's crown", "warp beacon"),):
        item = next((i for i in inventory if base_name(i) == name and "WEAR" in i.get("actions", [])), None)
        if item:
            p.mage_plan = {"kind": "choice", "choice": choice, "stage": "select", "steps": 0}
            return p.use(item, "WEAR", f"mage: choose {choice} for independent recovery/mobility")
    staff = p.staff(state)
    preservation = any(t["name"].lower() == "wand preservation" and t["points"] for t in state["hero"].get("talents", []))
    if not staff or not preservation or "magic missile" not in staff["name"].lower():
        return None
    candidates = [i for i in inventory if i.get("identified") and not i.get("known_cursed")
                  and "wand of " in i["name"].lower() and any(k in i["name"].lower() for k in ("frost", "disintegration", "prismatic light"))
                  and (state["hero"]["level"], i["name"]) not in p.imbue_attempts]
    if candidates:
        def score(i):
            return magic_score(dict(i, status="1/1", actions=["ZAP"]))
        item = max(candidates, key=score)
        if score(item) < score(staff):
            return None
        p.imbue_attempts.add((state["hero"]["level"], item["name"]))
        p.mage_plan = {"kind": "imbue", "choice": item["name"].lower(), "stage": "select", "steps": 0, "bags": set()}
        return p.use(staff, "IMBUE", "mage: inspect preservation-confirmed staff improvement")
    return None


def mage_menu(p, state):
    plan = p.mage_plan
    plan["steps"] += 1
    buttons = state["ui"]["buttons"]
    text = " ".join(state["ui"].get("texts", [])).replace("_", "").lower()
    if plan["kind"] == "warp":
        wanted = "clear beacon" if plan["stage"] == "clear" else "teleport to beacon" if plan["stage"] == "return" else "cancel"
        verified = plan["stage"] != "return" or f"on floor {state['depth']}." in text
        choice = next((b for b in buttons if b["label"].lower() == (wanted if verified else "cancel")), None)
        if choice:
            if wanted == "clear beacon":
                plan["stage"] = "set_after_clear"
            else:
                p.mage_plan = None
            return p.decision({"type": "button", "id": choice["id"]}, "mage: validated warp beacon control" if verified else "mage: cancel cross-floor warp")
        p.mage_plan = None
        return p.decision({"type": "back"}, "mage: cancel unexpected warp beacon menu")
    if plan["steps"] <= 6:
        if plan["stage"] == "select":
            names = ("warp beacon", "warping beacon") if plan["choice"] == "warp beacon" else (plan["choice"],)
            choice = next((b for b in buttons if any(name in b["label"].replace("_", "").lower() for name in names)), None)
            if choice:
                plan["stage"] = "confirm"
                return p.decision({"type": "button", "id": choice["id"]}, "mage: select planned progression option")
            if plan["kind"] == "imbue":
                bag = next((b for b in buttons if b["label"].lower() in {"magical holster", "backpack"}
                            and b["label"] not in plan["bags"]), None)
                if bag:
                    plan["bags"].add(bag["label"])
                    return p.decision({"type": "button", "id": bag["id"]}, "mage: find identified wand in observed bag")
        else:
            preserved = plan["kind"] != "imbue" or "will be returned at +0" in text
            choice = next((b for b in buttons if b["label"].lower().startswith(
                "yes, i'm sure" if plan["kind"] == "imbue" and preserved else
                "yes, i've made" if plan["kind"] == "choice" and plan["choice"] in text else "no,")), None)
            if choice:
                p.mage_plan = None
                return p.decision({"type": "button", "id": choice["id"]}, "mage: confirm verified progression" if preserved else "mage: refuse imbue without preservation")
    p.mage_plan = None
    return p.decision({"type": "back"}, "mage: cancel unavailable or unverified progression")


def warp_escape(p, state, enemies, distance):
    if not enemies or p.mage_plan or not p.warp_anchor or p.warp_cooldown:
        return None
    hero = state["hero"]
    depth, branch, target = p.warp_anchor
    if (depth, branch) != (state["depth"], state.get("branch", 0)) or depth % 5 == 0 \
            or hero["hp"] >= 0.55*hero["max_hp"] or not p.tiles.get(target, {}).get("visible"):
        return None
    width = state["map"]["width"]
    if not p.walkable(target, {o["cell"] for o in state.get("objects", [])}) or any(distance(target, e["cell"], width) < 4 for e in enemies):
        return None
    armor = next((i for i in state["inventory"] if i.get("equipped") and "ABILITY" in i.get("actions", [])
                  and (i.get("status") or "?").rstrip("%").isdigit()
                  and int(i["status"].rstrip("%")) >= 35), None)
    if armor:
        p.mage_plan = {"kind": "warp", "stage": "return", "anchor": p.warp_anchor, "steps": 0}
        p.warp_cooldown = 12
        return p.use(armor, "ABILITY", "mage: warp toward verified safe same-floor beacon", target=hero["cell"])
    return None


def ally_warp(p, state, enemies, distance):
    hero = state["hero"]
    points = next((t["points"] for t in hero.get("talents", []) if t["name"].lower() == "ally warp"), 0)
    if not points or not enemies or p.warp_cooldown or hero["hp"] >= 0.55*hero["max_hp"]:
        return None
    width = state["map"]["width"]
    candidates = []
    for obj in state.get("objects", []):
        # These names publicly identify the hero's mobile images. Never infer
        # alignment from an enemy class or from an unexported Java flag.
        if obj["name"].lower() not in {"mirror image", "prismatic image"}:
            continue
        cell = obj["cell"]
        if not 2 <= distance(cell, hero["cell"], width) <= 2*points or p.tiles.get(cell, {}).get("effects"):
            continue
        if cell in state.get("danger_cells", []) or not p.walkable(cell, ignored_neutrals={cell}):
            continue
        previous = p.paths(state, {e["cell"] for e in enemies}, ignored_neutrals={cell})
        separation = min(distance(cell, e["cell"], width) for e in enemies)
        if cell in previous and separation >= 4:
            candidates.append((separation, cell))
    if candidates:
        p.warp_cooldown = 12
        return p.cell(max(candidates)[1], "talent: instantaneous Ally Warp to public friendly image and safe ground")
    return None


def shield_battery(p, state, enemies):
    hero = state["hero"]
    if not enemies or hero["hp"] >= 0.4 * hero["max_hp"] or p.battery_cooldown:
        return None
    talent = next((t for t in hero.get("talents", []) if t["name"].lower() == "shield battery" and t["points"] > 0), None)
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    if not talent or any(s in buffs for s in ("shield", "barrier", "magic immun")):
        return None
    staff = p.staff(state)
    charges = (staff.get("status") or "?").split("/")[0] if staff else "?"
    if not charges.isdigit() or int(charges) < 1:
        return None
    # Shield Battery is an ordinary self-targeted wand cast. Do not test curses
    # or convert the staff: Backup Barrier and the next damaging zap remain usable.
    candidates = [i for i in state["inventory"] if "wand of " in i["name"].lower()
                  and "ZAP" in i.get("actions", []) and not i.get("known_cursed")
                  and (i.get("identified") or i.get("curse_known"))
                  and (i.get("status") or "?").split("/")[0].isdigit()
                  and int(i["status"].split("/")[0]) >= 2]
    if candidates:
        wand = min(candidates, key=lambda i: int(i["status"].split("/")[0]))
        p.battery_cooldown = 24
        return p.use(wand, "ZAP", "talent: spare-wand Shield Battery; retain charged staff", target=hero["cell"])
    return None
