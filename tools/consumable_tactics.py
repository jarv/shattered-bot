"""Learn consumables through ordinary use; quantity/depth clues are estimates."""
import re

try:
    from .upgrade_tactics import choose_upgrade
except ImportError:
    from upgrade_tactics import choose_upgrade


SCROLLS = {"upgrade", "identify", "remove curse", "transmutation", "teleportation", "recharging",
           "mirror image", "rage", "lullaby", "retribution", "terror", "magic mapping"}


def base_name(item):
    return re.sub(r" x\d+$", "", item["name"].lower())


def unknown_potion(item):
    return base_name(item).endswith(" potion") and not item.get("identified", False)


def unknown_scroll(item):
    name = base_name(item)
    return name.startswith("scroll of ") and name[10:] not in SCROLLS and not item.get("identified", False)


def identify_context(state):
    return tuple(sorted((i["name"], i.get("quantity", 1), bool(i.get("identified"))) for i in state["inventory"]))


def identify_retry_allowed(p, state):
    # READ remains in public item actions while blinded, but cannot execute.
    # Defer without poisoning inventory retry memory or opening menu intent.
    if any("blind" in b["name"].lower() for b in state["hero"].get("buffs", [])):
        return False
    return p.failed_identify_context != identify_context(state)


def learn_sources(p, state):
    depth = state["depth"]
    if any(base_name(i) == "potion of strength" for i in state["inventory"]) or any(
            base_name(o.get("top_item") or o) == "potion of strength" for o in state.get("objects", [])):
        p.strength_identified = True
    for obj in state.get("objects", []):
        item = obj.get("top_item")
        if item and not obj.get("for_sale") and (unknown_potion(item) or unknown_scroll(item)):
            p.consumable_sources.setdefault(base_name(item), set()).add(depth)
    counts = {base_name(i): i.get("quantity", 1) for i in state["inventory"]
              if unknown_potion(i) or unknown_scroll(i)}
    for name, quantity in counts.items():
        if quantity > p.consumable_inventory_counts.get(name, 0):
            p.consumable_sources.setdefault(name, set()).add(depth)
    p.consumable_inventory_counts = counts


def discovery_score(item, sources, kind="strength"):
    floors = sources.get(base_name(item), set())
    early = {d for d in floors if 1 <= d % 5 <= 4}
    # Strength has one guaranteed placement in each floor-pair; upgrades have
    # three across each region. Extra/random drops make these non-conclusive.
    pairs = {(d // 5, (d % 5 - 1) // 2) for d in early}
    return 2 * len(early) + item.get("quantity", 1) + (2 * len(pairs) if kind == "strength" else 0)


def choose_consumable(p, state, enemies, distance, neighbors):
    hero = state["hero"]
    pos, width, height = hero["cell"], state["map"]["width"], state["map"]["height"]
    buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
    active = [e for e in enemies if not e.get("sleeping")]
    hp = hero["hp"] / max(1, hero["max_hp"])
    safe = not enemies and not state.get("danger_cells") and not p.tiles[pos].get("effects") \
        and not p.tiles[pos].get("plant") and not p.tiles[pos].get("trap") \
        and not any(distance(pos, o["cell"], width) <= 3 for o in p.room_actors.values())
    safe = safe and not any(o["name"].lower() == "shopkeeper" and distance(pos, o["cell"], width) <= 5
                            for o in state.get("objects", []))
    if not active:
        strength = next((i for i in state["inventory"] if base_name(i) == "potion of strength"
                         and "DRINK" in i.get("actions", [])), None)
        if strength:
            return p.use(strength, "DRINK", "prepare: drink known strength potion")
        if any(base_name(i) == "scroll of upgrade" and "READ" in i.get("actions", []) for i in state["inventory"]) \
                and choose_upgrade(state):
            return None  # Take a justified known upgrade before risky discovery.
    if p.consumable_cooldown and not (active and hp < 0.35):
        p.consumable_cooldown -= 1
        return None
    # Stop the old full inventory / unidentified strength bottleneck. Use a real
    # identify scroll first; drink-testing is a deliberate risk if none is held.
    unknown = [i for i in state["inventory"] if unknown_potion(i) and "DRINK" in i.get("actions", [])]
    if safe and unknown and hp >= 0.8:
        identify = next((i for i in state["inventory"] if base_name(i) == "scroll of identify"
                         and "READ" in i.get("actions", [])), None)
        if identify and identify_retry_allowed(p, state):
            p.menu_plan = "discover-scroll"
            p.consumable_menu_bags = set()
            return p.use(identify, "READ", "identify: prioritize likely strength potion")
    scroll_reserve=0.7 if getattr(p,"pharmacophobia",False) and not getattr(p,"recent_threats",{}) else 0.85
    if safe and hp >= scroll_reserve and "starving" not in buffs and not any(s in buffs for s in ("blind", "poison", "burning", "paralys", "magic immun")):
        # Mage knows Upgrade at birth (HeroClass.initMage). For other future
        # policies, the most repeated early scroll is only a hypothesis to test.
        p.upgrade_known |= "mage" in hero["name"].lower() or any(base_name(i) == "scroll of upgrade" for i in state["inventory"])
        scrolls = [i for i in state["inventory"] if unknown_scroll(i) and "READ" in i.get("actions", [])
                   and base_name(i) not in p.tested_scrolls]
        if scrolls:
            identify = next((i for i in state["inventory"] if base_name(i) == "scroll of identify"
                             and "READ" in i.get("actions", [])), None)
            if identify:
                if not identify_retry_allowed(p, state):
                    return None
                p.menu_plan = "discover-scroll"
                p.consumable_menu_bags = set()
                return p.use(identify, "READ", "identify: reveal unknown scroll before risking its effect")
            item = max(scrolls, key=lambda i: discovery_score(i, p.consumable_sources, "upgrade"))
            p.tested_scrolls.add(base_name(item))
            p.menu_plan = "discover-scroll"
            p.consumable_menu_bags = set()
            p.consumable_cooldown = 12
            reason = "identify: read unknown scroll after upgrade is known" if p.upgrade_known else "identify: test likely upgrade scroll (unconfirmed)"
            return p.use(item, "READ", reason)
        exits = [c for c in neighbors(pos, width, height) if p.walkable(c) and p.tiles[c]["terrain"] not in {5, 7, 8, 21, 22, 37}
                 and not p.tiles[c].get("plant") and not p.loot.get(c, {}).get("for_sale")]
        if unknown and not getattr(p, "reserve_floor_puzzle_supplies", False) \
                and len(exits) >= 2 and not getattr(p, "pharmacophobia", False) and not any(o.get("top_item") and distance(pos, o["cell"], width) <= 1 for o in state.get("objects", [])):
            try:
                from .potion_discovery import room_ready
            except ImportError:
                from potion_discovery import room_ready
            if not room_ready(p,state):return None
            item = max(unknown, key=lambda i: discovery_score(i, p.consumable_sources))
            p.consumable_cooldown = 20
            return p.use(item, "DRINK", "identify: drink likely strength potion (unconfirmed)")
    if active and not state.get("danger_cells"):
        if hp < 0.5:
            for name, buff in (("potion of invisibility", "invisib"), ("potion of haste", "haste")):
                item = next((i for i in state["inventory"] if base_name(i) == name and "DRINK" in i.get("actions", [])), None)
                if item and buff not in buffs:
                    p.consumable_cooldown = 8
                    try:
                        from .room_supplies import use as use_room_supply
                    except ImportError:
                        from room_supplies import use as use_room_supply
                    return use_room_supply(p,item,"DRINK","potion: enable escape from dangerous combat",kind='emergency')
        if hp < 0.35:
            fear = next((i for i in state["inventory"] if base_name(i) == "stone of fear"
                         and "THROW" in i.get("actions", [])), None)
            close = [e for e in active if distance(pos, e["cell"], width) == 1
                     and p.shot_clear(state, e["cell"]) and (not fear or p.target_allowed(fear, e))]
            if fear and close:
                p.consumable_cooldown = 8
                return p.use(fear, "THROW", "stone: fear adjacent attacker at critical health", target=close[0]["cell"])
            images = any(o["name"].lower() in {"mirror image", "prismatic image"} for o in state.get("objects", []))
            for name in ("scroll of teleportation", "scroll of terror", "scroll of mirror image"):
                if name == "scroll of mirror image" and images:
                    continue
                item = next((i for i in state["inventory"] if base_name(i) == name
                             and "READ" in i.get("actions", [])), None)
                if item:
                    p.consumable_cooldown = 8
                    return p.use(item, "READ", "scroll: escape or distract enemies at critical health")
        if len(p.charged_magic(state)) == 0 and "recharging" not in buffs:
            item = next((i for i in state["inventory"] if base_name(i) == "scroll of recharging" and "READ" in i.get("actions", [])), None)
            if item:
                p.consumable_cooldown = 8
                return p.use(item, "READ", "scroll: recharge exhausted combat arsenal")
        # Start with compact, predictable effects. Gas and levitation puzzle
        # routes need separate area/duration planning and remain deferred.
        targets = [e for e in active if distance(pos, e["cell"], width) >= 3 and p.shot_clear(state, e["cell"])
                   and e["name"].lower() not in {"marsupial rat", "albino rat", "sewer snake"}]
        for enemy in targets:
            bar = enemy.get("health_bar")
            if bar and bar[1] and bar[0] / bar[1] < 0.4:
                continue
            if any(distance(enemy["cell"], o["cell"], width) <= 1 and (o.get("top_item") or o["name"].lower() not in {e["name"].lower() for e in enemies}) for o in state.get("objects", [])):
                continue
            for name in ("potion of frost", "potion of liquid flame"):
                item = next((i for i in state["inventory"] if base_name(i) == name and "THROW" in i.get("actions", [])), None)
                if not item or ("flame" in name and p.tiles.get(enemy["cell"], {}).get("terrain") == 29):
                    continue
                if name=='potion of liquid flame' and getattr(p,'reserve_floor_puzzle_supplies',False) \
                        and hp>=.5 and item.get('quantity',1)==1 \
                        and any(t['terrain'] in {13,27} for t in p.tiles.values()):
                    continue  # Keep the last known ignition source for observed wood; emergencies may spend it.
                try:
                    from .room_supplies import eligible_target, use as use_room_supply
                except ImportError:
                    from room_supplies import eligible_target, use as use_room_supply
                if hp>=.5 and not p.item_action_allowed(item,"THROW"):continue
                if not (eligible_target(p,item,enemy,'emergency') if hp<.5 else p.target_allowed(item, enemy)):
                    continue
                if "flame" in name and any(p.tiles.get(c, {}).get("terrain") in {2, 15, 30} for c in neighbors(pos, width, height)):
                    continue
                p.consumable_cooldown = 10
                if hp<.5:
                    return use_room_supply(p,item,"THROW","potion: ranged control/damage against durable enemy",
                                           kind='emergency',target=enemy["cell"])
                return p.use(item, "THROW", "potion: ranged control/damage against durable enemy", target=enemy["cell"])
    return None


def discovery_menu(p, state):
    texts = " ".join(state["ui"].get("texts", [])).lower()
    buttons = state["ui"]["buttons"]
    if "cancel this scroll usage" in texts:
        yes = next((b for b in buttons if b["label"].lower().startswith("yes, i'm positive")), None)
        if yes:
            p.menu_plan = None
            return p.decision({"type": "button", "id": yes["id"]}, "identify: accept already-consumed scroll cancellation")
    if "upgrade an item" in texts:
        p.menu_plan = "upgrade-select"
        return p.menu(state)
    if "identify an item" in texts:
        items = sorted((i for i in state["inventory"] if not i.get("identified", False)),
                       key=lambda i: (unknown_potion(i), unknown_scroll(i),
                                      discovery_score(i, p.consumable_sources)), reverse=True)
    elif "cleanse an item" in texts:
        try:
            from .combat_items import accessory_kind
        except ImportError:
            from combat_items import accessory_kind
        items = sorted((i for i in state["inventory"] if i.get("known_cursed") or i.get("equipped")),
                       key=lambda i: (bool(i.get('known_cursed') and i.get('equipped') and accessory_kind(i)),
                                      bool(i.get('known_cursed') and i.get('equipped')),
                                      i.get("known_cursed", False), i.get("equipped", False)), reverse=True)
    else:
        items = []  # In particular, do not blindly transmute valuable equipment.
    # Preserve preferred consumables across bag navigation rather than consuming
    # Identify on lower-ranked equipment while the target is in another bag.
    preferred_consumable = bool(items and (unknown_potion(items[0]) or unknown_scroll(items[0])))
    for item in items[:1] if preferred_consumable else items:
        button = next((b for b in buttons if b["label"].lower() == item["name"].lower()), None)
        if button:
            p.menu_plan = None
            return p.decision({"type": "button", "id": button["id"]}, "identify: choose useful scroll target")
    if items:
        bags = ("potion bandolier", "backpack", "scroll holder", "magical holster", "velvet pouch")
        bag = next((b for name in bags for b in buttons if b["label"].lower() == name
                    and b["label"] not in p.consumable_menu_bags), None)
        if bag:
            p.consumable_menu_bags.add(bag["label"])
            return p.decision({"type": "button", "id": bag["id"]}, "identify: open item bag")
    if "identify an item" in texts:
        p.failed_identify_context = identify_context(state)
    return p.decision({"type": "back"}, "identify: cancel unsafe or unavailable scroll target")
