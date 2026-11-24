"""Budgeted alchemy through visible stations, bag buttons, and recipe previews."""
from dataclasses import dataclass
import re

try:
    from .consumable_tactics import base_name, unknown_potion, unknown_scroll
except ImportError:
    from consumable_tactics import base_name, unknown_potion, unknown_scroll


@dataclass(frozen=True)
class Brew:
    ingredients: tuple
    output: str
    reason: str
    energy: int = 0
    fallback: str | None = None


SEED_POTIONS = {
    "blindweed": "invisibility", "mageroyal": "purity", "earthroot": "paralytic gas",
    "fadeleaf": "mind vision", "firebloom": "liquid flame", "icecap": "frost",
    "sorrowmoss": "toxic gas", "starflower": "experience", "stormvine": "levitation",
    "swiftthistle": "haste",
}


def plan_brew(state, demands=(), *, barren_land=False):
    """Do not turn scarce upgrades, the last escape, or healing into experiments."""
    inventory = state["inventory"]
    counts = {base_name(i): i.get("quantity", 1) for i in inventory}
    unknown = sum(unknown_potion(i) or unknown_scroll(i) for i in inventory)
    buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
    if counts.get("potion of purity") and "starving" in buffs and "gas" not in demands:
        return Brew(("potion of purity",), "potion of cleansing", "urgent satiety without Pharmacophobia", 4)
    raw = counts.get("mystery meat", 0)
    edible = any('EAT' in i.get('actions',[]) and not any(k in base_name(i)
                 for k in ('seed','mystery meat','blandfruit','sunfruit')) for i in inventory)
    if 'starving' in buffs and edible:
        return None  # Eat carried safe food before paying cooking/menu turns.
    if raw:
        amount = 3 if raw >= 3 else 1
        return Brew(("mystery meat",)*amount, "stewed meat", "cook carried raw food before optional brewing", 2 if amount == 3 else 1)
    try:
        from .blandfruit_tactics import recipe
    except ImportError:
        from blandfruit_tactics import recipe
    fruit=recipe(counts,demands,state.get('policy_rules',{}).get('pharmacophobia',False))
    if fruit:
        return Brew(fruit[0],fruit[1],"cook Blandfruit with a known seed; retain quest and recovery reserves")
    if "fall" in demands and not counts.get("elixir of feather fall") \
            and counts.get("potion of levitation",0) >= (2 if "flight" in demands else 1):
        return Brew(("potion of levitation",),"elixir of feather fall",
                    "protect a publicly observed distant-well descent; levitation alone does not prevent landing damage",10)
    if counts.get("potion of purity", 0) >= 2:
        reason='full satiety bypasses On Diet; retain gas-room protection' if state.get('policy_rules',{}).get('on_diet',False) \
            else 'full satiety; retain gas-room protection'
        return Brew(("potion of purity",), "potion of cleansing", reason, 4)
    if counts.get("scroll of identify", 0) and unknown >= 3:
        return Brew(("scroll of identify",), "scroll of divination", "identify four types without poisonous drink-testing", 6)
    if counts.get("magical catalyst", 0):
        return Brew(("magical catalyst",), "trinket",
                    "turn the observed magical catalyst into the best offered Mage trinket", 6)
    if counts.get("scroll of lullaby", 0) >= 2 and not counts.get("stone of deep sleep"):
        return Brew(("scroll of lullaby",), "stone of deep sleep", "two targeted disengagement stones; retain one recovery scroll")
    if counts.get("scroll of mirror image", 0) >= 2 and state["hero"]["level"] >= 12 and not counts.get("scroll of prismatic image"):
        return Brew(("scroll of mirror image",), "scroll of prismatic image", "durable image distracts swarms and supports Ally Warp", 6, "stone of flock")
    artifacts = [i for i in inventory if i.get("equipped") and any(a in i.get("actions", []) for a in ("CAST", "ACTIVATE", "SNACK", "BREW", "ROOT", "STEAL"))]
    if len(artifacts) >= 2 and counts.get("scroll of recharging", 0) >= 3 and not counts.get("scroll of mystical energy"):
        return Brew(("scroll of recharging",), "scroll of mystical energy", "artifact recharge supports mobility, Horn and direct seed abilities", 6, "stone of shock")
    for source, output, reserve in (
        ("scroll of recharging", "stone of shock", 1),
        ("scroll of teleportation", "stone of blink", 1),
        ("scroll of terror", "stone of fear", 1),
        ("scroll of rage", "stone of aggression", 0),
        ("scroll of magic mapping", "stone of clairvoyance", 1),
        ("scroll of mirror image", "stone of flock", 1),
    ):
        if counts.get(source, 0) > reserve and not counts.get(output):
            return Brew((source,), output, "targeted control while retaining last general-purpose escape/recharge")
    for source, output, reserve in (
        ("potion of haste", "potion of stamina", 1),
        ("potion of frost", "potion of snap freeze", 1),
        ("potion of paralytic gas", "potion of earthen armor", 0),
        ("potion of invisibility", "potion of shrouding fog", 1),
    ):
        if counts.get(source, 0) > reserve and not counts.get(output):
            return Brew((source,), output, "known non-healing exotic improves control or mobility", 4)
    requested={"frost":"frost","flame":"liquid flame","gas":"purity","sentry":"haste",
               "flight":"levitation","fall":"levitation","pool":"invisibility"}
    needed={requested[d] for d in demands if d in requested}
    for kind in sorted(SEED_POTIONS,key=lambda k:SEED_POTIONS[k] not in needed):
        name = f"seed of {kind}"
        if counts.get(name, 0) >= 3:
            return Brew((name, name, name), "random potion", f"three matching {kind} seeds yield identified {SEED_POTIONS[kind]}; no planting")
    seeds = [name for kind in SEED_POTIONS if counts.get(name := f"seed of {kind}", 0)]
    if barren_land:
        # Prefer the existing matching-seed recipes above. Mixed leftovers are
        # useful even without bag pressure when ordinary plants cannot sprout.
        # Leave rare experience seeds for a matching recipe when possible.
        mixed = [name for name in seeds if name != "seed of starflower"
                 and SEED_POTIONS[name.removeprefix("seed of ")] not in needed
                 for _ in range(min(2, counts[name]))]
        if len(mixed) >= 3:
            return Brew(tuple(mixed[:3]), "random potion",
                        "Barren Land: brew unusable planting seeds; verify actual potion identity")
        return None  # Bag pressure must not override the recipe/rare-seed reserves.
    if len(inventory) >= 18 and len(seeds) >= 3:
        return Brew(tuple(seeds[:3]), "random potion", "relieve seed inventory pressure; output identity remains unknown until observed")
    return None


def context(state):
    return (state["depth"],state['hero'].get('level'),
            tuple(sorted((i["name"], i.get("quantity", 1),i.get('status') or '',bool(i.get('equipped')))
                         for i in state["inventory"])))


def rendered_energy(state):
    value=state.get('ui',{}).get('energy_text','') or ''
    match=re.fullmatch(r'energy\s*:?\s*(\d+)(?:\+(\d+))?',value.lower().strip())
    return tuple(int(v or 0) for v in match.groups()) if match else None


def toolkit_energy(item):
    status=(item or {}).get('status') or ''
    # Percentages are warm-up progress, not available energy.
    return int(status) if status.isdigit() and item.get('identified') and not item.get('known_cursed') else 0


def observe_energy(p,before,state):
    energy=rendered_energy(state)
    if state.get('scene')=='AlchemyScene' and energy:
        p.alchemy_energy=energy[0]  # Keep global and toolkit reserves separate.
    if not before or before.get('depth')!=state.get('depth'):return
    decision=getattr(p,'last_decision',None)
    action=decision.action if decision else {}
    cell=action.get('cell')
    # A plausible ordinary pickup/spending receipt invalidates the cache; it
    # does not infer the new amount. Inspect the rendered energy label again.
    pickup=action.get('type')=='cell' and state.get('hero',{}).get('cell')==cell and any(
        o.get('cell')==cell and 'energy crystal' in base_name(o.get('top_item',o))
        for o in before.get('objects',[]))
    spent=action.get('type')=='item' and action.get('action')=='ENERGIZE'
    if pickup or spent:
        p.alchemy_energy=None
        p.alchemy_attempts.clear()


def inventory_baseline(state, brew):
    names = {*brew.ingredients, brew.output}
    if brew.output == 'dreamfruit' and brew.ingredients == ('blandfruit', 'seed of mageroyal'):
        names.add('magefruit')  # Rendered name of this known recipe.
    if brew.fallback:names.add(brew.fallback)
    if brew.output == 'trinket':
        try:
            from .trinket_tactics import TRINKETS
        except ImportError:
            from trinket_tactics import TRINKETS
        names.update(TRINKETS)
    return {name: sum(i.get('quantity', 1) for i in state['inventory']
                      if base_name(i) == name) for name in names}


def approach_alchemy(p, state, urgent=False):
    if p.alchemy_plan or context(state) in p.alchemy_attempts:
        return None
    demands = {"gas"} if any("gas" in n.get("kind", "") for n in p.room_notes) else set()
    try:
        from .puzzle_supplies import demands as room_demands
    except ImportError:
        from puzzle_supplies import demands as room_demands
    distance = lambda a,b,w: max(abs(a%w-b%w),abs(a//w-b//w))
    demands.update(d.kind for d in room_demands(p,state,distance))
    brew = plan_brew(state, demands, barren_land=getattr(p, "barren_land", False))
    if not brew:
        return None
    if urgent and brew.output not in {"potion of cleansing", "stewed meat",
                                    "dreamfruit","fadefruit","sunfruit","starfruit","swiftfruit","blindfruit"}:
        return None
    toolkit = next((i for i in state["inventory"] if i.get("equipped")
                    and "alchemist's toolkit" in i["name"].lower()
                     and "BREW" in i.get("actions", [])), None)
    if toolkit and (toolkit.get('status') or '').endswith('%'):
        toolkit=None  # Warming toolkit cannot brew even though BREW is displayed.
    reserve=0 if "starving" in " ".join(b["name"].lower() for b in state["hero"].get("buffs", [])) else 2
    global_energy=getattr(p,'alchemy_energy',None)
    if brew.energy and global_energy is not None and global_energy+toolkit_energy(toolkit)<brew.energy+reserve:
        if brew.fallback:
            brew=Brew(brew.ingredients,brew.fallback,brew.reason+'; affordable free fallback')
        else:
            p.planner.report['alchemy_energy']={'status':'deferred','required':brew.energy+reserve,
                'global_energy':global_energy,'toolkit_energy':toolkit_energy(toolkit),
                'reason':'Continue ordinary play until energy changes; no ingredients or energizing spent'}
            return None
    if toolkit:
        p.alchemy_attempts.add(context(state))
        p.alchemy_plan = {"brew": brew, "index": 0, "stage": "energy" if brew.energy else "slot", "steps": 0,
                          "inventory_before":inventory_baseline(state,brew),
                          "reserve": 0 if "starving" in " ".join(b["name"].lower() for b in state["hero"].get("buffs", [])) else 2}
        return p.use(toolkit, "BREW", f"alchemy: portable toolkit; {brew.reason}")
    paths = p.paths(state)
    pos, width = state["hero"]["cell"], state["map"]["width"]
    stations = [c for c, t in p.tiles.items() if t["terrain"] == 28 and t.get("visible")]
    choices = []
    for station in stations:
        for bank in paths:
            if max(abs(bank % width - station % width), abs(bank // width - station // width)) == 1:
                route = p.route(paths, bank)
                if len(route) <= 6:
                    choices.append((len(route), station, bank))
    if not choices:
        return None
    _, station, bank = min(choices)
    if pos != bank:
        return p.toward(state, bank, "alchemy: approach nearby visible station", paths)
    p.alchemy_attempts.add(context(state))
    p.alchemy_plan = {"brew": brew, "index": 0, "stage": "energy" if brew.energy else "slot", "steps": 0,
                      "inventory_before":inventory_baseline(state,brew),
                      "reserve": 0 if "starving" in " ".join(b["name"].lower() for b in state["hero"].get("buffs", [])) else 2}
    return p.cell(station, f"alchemy: open station; {brew.reason}")


def alchemy_menu(p, state):
    plan = p.alchemy_plan
    if not plan:
        return leave_alchemy(p,state,"alchemy: leave unplanned station")
    plan["steps"] += 1
    buttons = state["ui"]["buttons"]
    def button(label):
        return next((b for b in buttons if base_name({"name": b["label"]}) == label), None)
    brew = plan["brew"]
    energy=rendered_energy(state)
    if energy:p.alchemy_energy=energy[0]
    if plan['stage']=='energy':
        required=brew.energy+plan.get('reserve',2)
        if not energy or sum(energy)<required:
            if energy and brew.fallback:
                brew=plan['brew']=Brew(brew.ingredients,brew.fallback,brew.reason+'; affordable free fallback')
            else:
                p.planner.report['alchemy_energy']={'status':'deferred','required':required,
                    'available':sum(energy) if energy else None,
                    'reason':'Inspected energy only; no ingredient selection or craft attempted'}
                p.alchemy_plan=None
                return leave_alchemy(p,state,'alchemy: defer until minimum recipe energy is observed')
        plan['stage']='slot'
    if brew.output == 'trinket':
        try:
            from .trinket_tactics import trinket_menu
        except ImportError:
            from trinket_tactics import trinket_menu
        choice = trinket_menu(p,state)
        if choice:
            return choice
    if plan["steps"] <= 18:
        if plan["stage"] == "slot":
            if plan["index"] < len(brew.ingredients):
                add = button("add item")
                if add:
                    plan["stage"] = "bag"
                    return p.decision({"type": "button", "id": add["id"]}, "alchemy: select empty input")
            else:
                craft = button("craft: " + brew.output)
                energy = re.fullmatch(r"energy\s*:?\s*(\d+)(?:\+(\d+))?", state["ui"].get("energy_text", "").lower().strip())
                available = sum(int(n) for n in energy.groups() if n is not None) if energy else 0
                if brew.energy and (not energy or available < brew.energy+plan.get("reserve", 2)):
                    craft = None
                output = brew.output
                # The played English UI renders the dreamfruit recipe as
                # magefruit. Admit only that exact known ingredient recipe and
                # an offered craft button; keep the actual name for receipts.
                if not craft and brew.output == 'dreamfruit' \
                        and brew.ingredients == ('blandfruit', 'seed of mageroyal'):
                    craft = button("craft: magefruit")
                    if craft:
                        output = 'magefruit'
                if not craft and brew.fallback:
                    craft = button("craft: " + brew.fallback)
                    output = brew.fallback
                if craft:
                    plan["stage"] = "done"
                    plan["crafted_output"]=output
                    if 'inventory_before' in plan:
                        before = dict(plan['inventory_before'])
                        # Alchemy scenes may omit inventory. The saved public
                        # baseline already contains the planned output count.
                        if output not in before and state.get('inventory') is not None:
                            before[output] = sum(i.get('quantity', 1) for i in state['inventory']
                                                 if base_name(i) == output)
                        if output in before:
                            plan['before_counts'] = before
                    return p.decision({"type": "button", "id": craft["id"]}, f"alchemy: craft verified {output}")
        elif plan["stage"] == "bag":
            ingredient = button(brew.ingredients[plan["index"]])
            if ingredient:
                plan["index"] += 1
                plan["stage"] = "slot"
                return p.decision({"type": "button", "id": ingredient["id"]}, "alchemy: add planned ingredient")
            name = brew.ingredients[plan["index"]]
            bag_name = "velvet pouch" if name.startswith("seed of ") else "scroll holder" if name.startswith("scroll of ") else "potion bandolier" if name.startswith("potion of ") else "backpack"
            key = (plan["index"], bag_name)
            visited = plan.setdefault("bags", set())
            bag = button(bag_name)
            if bag and key not in visited:
                visited.add(key)
                return p.decision({"type": "button", "id": bag["id"]}, "alchemy: open ingredient bag once")
    if plan.get('stage')=='done' and 'before_counts' in plan and state.get('inventory') is not None:
        output=plan['crafted_output'];before=plan['before_counts']
        after={name:sum(i.get('quantity',1) for i in state['inventory'] if base_name(i)==name)
               for name in before}
        p.planner.report['alchemy_receipt']={'output':output,
            'output_inventory_increased':after[output]>before[output],
            'ingredients_consumed':all(after[name]<=before[name]-brew.ingredients.count(name)
                                       for name in set(brew.ingredients)),
            'qualification':'Observed inventory differences only; recipe preview/craft input is not collection'}
    # No guessed recipe choice, automatic energizing, repeated cancel, or substitute.
    p.alchemy_plan = None
    return leave_alchemy(p,state,"alchemy: exit after completion or unavailable verified recipe")


def leave_alchemy(p,state,reason):
    # Scene ExitButton is a visible ordinary button, not a dismissible Window.
    if state.get('scene')=='AlchemyScene' and not state.get('modal'):
        back=next((b for b in state['ui'].get('buttons',[]) if b['label'].strip().lower()=='back'),None)
        if back:return p.decision({'type':'button','id':back['id']},reason)
        p.stop_unsafe('Alchemy scene has no observed exit button; cannot safely leave through window dismissal')
    return p.decision({'type':'back'},reason)
