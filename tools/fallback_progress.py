"""Bound accepted no-progress fallback waits, not deliberate tactical recovery."""

import json


class FallbackProgress:
    def __init__(self, limit=128):
        self.limit = limit
        self.waits = 0

    @staticmethod
    def progress(state):
        hero = state.get("hero", {})
        # Ignore clock ticks, UI flicker and passive wand/artifact recharging:
        # those must not turn an unchanged locked floor into endless progress.
        return json.dumps({
            "depth": state.get("depth"), "branch": state.get("branch", 0),
            "status": state.get("status"), "modal": state.get("modal"),
            "hero": {k: hero.get(k) for k in ("cell", "hp", "max_hp", "level", "gold", "strength")},
            "buffs": sorted(b.get("name", "") for b in hero.get("buffs", [])),
            "map": sorted((t["cell"], t["terrain"], t.get("trap"), t.get("plant"))
                          for t in state.get("map", {}).get("cells", [])),
            "objects": sorted(((o.get("cell"), o.get("name"), o.get("health_bar"))
                               for o in state.get("objects", [])), key=repr),
            "inventory": sorted((i.get("id", ""), i.get("name", ""), i.get("quantity", 1))
                                for i in state.get("inventory", [])),
            "keys": state.get("keys", []), "danger": sorted(state.get("danger_cells", [])),
            "boss_bar": state.get("boss_health_text"),
        }, sort_keys=True)

    def observe(self, before, decision, after):
        fallback = decision.action == {"type": "wait"} and decision.reason in {
            "last resort: advance time and accept damage; no verified safe action",
            "until death: advance time after admitted gameplay recovery is exhausted",
        }
        if fallback and self.progress(before) == self.progress(after):
            self.waits += 1
        else:
            self.waits = 0
        return self.waits >= self.limit
