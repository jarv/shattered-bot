#!/usr/bin/env python3
"""Regular Mage policy with explicitly configured optional challenge rules."""
import sys

try:
    from .exploration_budget import selective_descent, pressure as exploration_pressure, starving_food, food_loot
except ImportError:
    from exploration_budget import selective_descent, pressure as exploration_pressure, starving_food, food_loot

try:
    from .survival_policy import SurvivalPolicy, is_hostile
    from .policy_decision import Finished, Intent
    from .policy_geometry import distance, neighbors, line_clear
    from .challenge_rules import ChallengeRules, CHALLENGES
    from .consumable_tactics import base_name, unknown_potion
    from .alchemy_tactics import approach_alchemy, alchemy_menu
    from .artifact_tactics import use_artifact
    from .mage_tactics import shield_battery, prepare_mage, mage_menu, warp_escape, ally_warp
    from .challenge_combat import ChallengeCombat, champion, magic_factor, enemy_line, exposure, reach
    from .environment_tactics import trigger_trap, use_bomb, observe_bombs
    from .hidden_doors import seek_corridor_end
    from .doorway_tactics import doorway_first, hold_doorway, reset_snake_door
    from .special_rooms import fire_barrier
    from .ghost_quest import observe_quest, visit_ghost, quest_menu, quest_combat
    from .puzzle_supplies import prepare_supplies, identify_menu, recover_probe, demands as supply_demands, frost_recovery_nearby
    from .potion_stash import advance_stash
    from .public_evidence import bind_threat
    from .room_tactics import charge_suspect_container
    from .wand_tactics import choose_transfusion, observe_wand_cast
    from .environment_tactics import recover_trap_payload
    from .mimic_hunt import observe_hunts, hunt_missing_mimic, crystal_mimic
    from .room_loot import before_room_exit
    from .snake_tactics import seek_next_door
    from .tactical_recovery import recover as recover_tactic, locked_room_route
    from .mimic_tactics import fight_mimic
    from .drop_tactics import prepare_drop, drop_menu, recover_drop
    from .room_completion import obligations
    from .seed_startup import normalize, seed_menu
    from .runestone_tactics import choose_runestone, prepare_intuition, intuition_menu, prepare_mapping, prepare_inventory_stone, inventory_stone_menu, blink_escape
    from .room_tactics import plan_journey, extinguish, controlled_burn, prepare_containers, crystal_choice, awareness_well, investigate_suspect_container, suspect_container_pending
    from .boss_strategies import create_mage_strategies, goo_blast_reaches
except ImportError:
    from survival_policy import SurvivalPolicy, is_hostile
    from policy_decision import Finished, Intent
    from policy_geometry import distance, neighbors, line_clear
    from challenge_rules import ChallengeRules, CHALLENGES
    from consumable_tactics import base_name, unknown_potion
    from alchemy_tactics import approach_alchemy, alchemy_menu
    from artifact_tactics import use_artifact
    from mage_tactics import shield_battery, prepare_mage, mage_menu, warp_escape, ally_warp
    from challenge_combat import ChallengeCombat, champion, magic_factor, enemy_line, exposure, reach
    from environment_tactics import trigger_trap, use_bomb, observe_bombs
    from hidden_doors import seek_corridor_end
    from doorway_tactics import doorway_first, hold_doorway, reset_snake_door
    from special_rooms import fire_barrier
    from ghost_quest import observe_quest, visit_ghost, quest_menu, quest_combat
    from puzzle_supplies import prepare_supplies, identify_menu, recover_probe, demands as supply_demands, frost_recovery_nearby
    from potion_stash import advance_stash
    from public_evidence import bind_threat
    from room_tactics import charge_suspect_container
    from wand_tactics import choose_transfusion, observe_wand_cast
    from environment_tactics import recover_trap_payload
    from mimic_hunt import observe_hunts, hunt_missing_mimic, crystal_mimic
    from room_loot import before_room_exit
    from snake_tactics import seek_next_door
    from tactical_recovery import recover as recover_tactic, locked_room_route
    from mimic_tactics import fight_mimic
    from drop_tactics import prepare_drop, drop_menu, recover_drop
    from room_completion import obligations
    from seed_startup import normalize, seed_menu
    from runestone_tactics import choose_runestone, prepare_intuition, intuition_menu, prepare_mapping, prepare_inventory_stone, inventory_stone_menu, blink_escape
    from room_tactics import plan_journey, extinguish, controlled_burn, prepare_containers, crystal_choice, awareness_well, investigate_suspect_container, suspect_container_pending
    from boss_strategies import create_mage_strategies, goo_blast_reaches


POISONOUS = {"potion of healing", "potion of shielding", "elixir of honeyed healing",
             "elixir of aquatic rejuvenation", "sunfruit"}


class MagePolicy(SurvivalPolicy):
    _legacy_all_nine_verification=False
    # Shared tactics read these aliases; the immutable configuration is the only
    # source of truth, rather than independent class booleans or mutable copies.
    hostile_champions=property(lambda self:self.rules.hostile_champions)
    badder_bosses=property(lambda self:self.rules.badder_bosses)
    on_diet=property(lambda self:self.rules.on_diet)
    faith_is_my_armor=property(lambda self:self.rules.faith_is_my_armor)
    pharmacophobia=property(lambda self:self.rules.pharmacophobia)
    barren_land=property(lambda self:self.rules.barren_land)
    swarm_intelligence=property(lambda self:self.rules.swarm_intelligence)
    into_darkness=property(lambda self:self.rules.into_darkness)
    forbidden_runes=property(lambda self:self.rules.forbidden_runes)
    def __init__(self, goal="survival", engine="legacy", seed=None, rules=None,
                 stop_on_no_safe_action=False,stop_on_incomplete_loot=False,unit_strategy_overrides=None):
        super().__init__(goal=goal, engine=engine)
        if rules is not None and not isinstance(rules,ChallengeRules):
            raise ValueError('rules must be a ChallengeRules configuration')
        self.rules=rules if rules is not None else ChallengeRules()
        try:
            from .unit_profiles import StrategyBook
        except ImportError:
            from unit_profiles import StrategyBook
        self.unit_strategies=StrategyBook(unit_strategy_overrides)
        if not isinstance(stop_on_no_safe_action,bool) or not isinstance(stop_on_incomplete_loot,bool):
            raise ValueError('Stop-policy options must be explicit booleans')
        self.stop_on_no_safe_action=stop_on_no_safe_action
        self.stop_on_incomplete_loot=stop_on_incomplete_loot
        self.enabled_challenges=self.rules.enabled_challenges
        self.verified_challenges=()
        self.challenges_verified = False
        self.challenge_window_opened = False
        self.startup_options_opened = False
        self.alchemy_plan = None
        self.alchemy_attempts = set()
        self.wandmaker_quest = {}
        self.wandmaker_menu = None
        self.artifact_cooldown = 0
        self.artifact_menu = None
        self.battery_cooldown = 0
        self.challenge_combat = ChallengeCombat()
        self.doorway_lure_cost = {}
        self.doorway_hold = None
        self.floor_recovery = 0
        self.stone_cooldown = 0
        self.room_journey = None
        self.room_attempts = set()
        self.boss_strategies = create_mage_strategies()
        self.artifact_swap = None
        self.beacon_anchor = None
        self.beacon_floor = None
        self.scry_attempts = set()
        self.mage_plan = None
        self.imbue_attempts = set()
        self.intuition_plan = None
        self.intuition_attempts = set()
        self.artifact_feed_attempts = set()
        self.warp_anchor = None
        self.warp_setup_floor = None
        self.warp_cooldown = 0
        self.mapping_attempts = set()
        self.inventory_stone_plan = None
        self.inventory_stone_attempts = set()
        self.enemy_inspection = None
        self.inspection_cache = None
        self.inspection_inputs = 0
        self.deferred_crystal_doors = set()
        self.trap_attempts = set()
        self.bomb_cells = set()
        self.ghost_quest = {"stage":"new", "travel":0}
        self.ghost_menu = None
        self.unseen_damage_turns = 0
        self.unseen_damage_cell = None
        self.last_safe_cell = None
        self.puzzle_guesses = set()
        self.puzzle_drinks = set()
        self.puzzle_probe = None
        self.potion_probe_permit = None
        self.puzzle_identify_plan = None
        self.puzzle_identify_attempts = set()
        self.drop_plan = None
        self.drop_attempts = set()
        self.completed_room_rewards = set()
        self.resolved_crystal_alternatives = set()
        self.crystal_choice_groups = {}
        self.requested_seed = normalize(seed)
        self.verified_seed = None
        self.seed_steps = 0
        self.seed_submitted = False
        self.seed_options_opened = False

    def item_action_allowed(self, item, action):
        name = base_name(item)
        try:
            from .room_supplies import allowed as room_supply_allowed
        except ImportError:
            from room_supplies import allowed as room_supply_allowed
        if not room_supply_allowed(self,item,action):return False
        if action == 'EAT':
            try:
                from .blandfruit_tactics import HARMFUL_FOOD
            except ImportError:
                from blandfruit_tactics import HARMFUL_FOOD
            if name in HARMFUL_FOOD:return False
        if (self.wandmaker_quest.get('variant')=='berry' and self.wandmaker_quest.get('stage')=='active'
                and action in {'ZAP','THROW','PLANT'}
                and any(n in name for n in ('fireblast','liquid flame','firebloom','firefruit'))):
            return False
        if self.barren_land and (action == "PLANT" or (action == "THROW" and name.startswith("seed of "))):
            return False
        if self.pharmacophobia and action == "DRINK" and unknown_potion(item):
            return self.potion_probe_permit == (item.get("id"),item["name"])
        if self.pharmacophobia and action in {"DRINK", "EAT"} and name in POISONOUS:
            return False
        return super().item_action_allowed(item, action)

    def food_items(self, state):
        return [i for i in state.get('inventory',[]) if 'EAT' in i.get('actions',[])
                and (base_name(i)=='blandfruit chunks' or not any(raw in base_name(i)
                     for raw in ('seed','mystery meat','blandfruit')))
                and self.item_action_allowed(i, "EAT")]

    def decision(self, action, reason, *, intent=Intent.OTHER):
        decision = super().decision(action, reason, intent=intent)
        self.planner.report.update(selection=reason, challenge_mode=self.rules.mode,
                                   floor_recovery_inputs=self.floor_recovery)
        if self.inspection_cache:
            self.planner.report["inspected_enemy"] = dict(self.inspection_cache, buffs=sorted(self.inspection_cache["buffs"]))
        if action["type"] not in {"inspect", "back"}:
            self.inspection_cache = None  # No status knowledge survives a world-changing input.
        return decision

    def harmless_effect(self, description):
        try:
            from .garden_tactics import garden_effect
        except ImportError:
            from garden_tactics import garden_effect
        return description.strip().lower() == "a cloud of thick black smoke is swirling here." or garden_effect(description)

    def target_allowed(self, item, enemy):
        if enemy['name'].lower()=='rot lasher':return False
        if any(action in item.get('actions',[]) and not self.item_action_allowed(item,action)
               for action in ('ZAP','THROW')):
            return False
        if enemy['name'].lower() in {'rot heart','rot lasher'}:
            name=base_name(item)
            if 'ZAP' in item.get('actions',[]) and not any(n in name for n in
                    ('magic missile','frost','disintegration','lightning','prismatic light')):
                return False
            if any(n in name for n in ('fire','flame','blast','corrosion','corruption')):return False
        name = base_name(item)
        enemy_name = enemy["name"].lower()
        if name in {"stone of fear", "stone of deep sleep", "stone of aggression"} and (
            enemy_name in self.boss_strategies or "fist" in enemy_name
            or enemy_name in {"demon spawner", "fetid rat", "gnoll trickster", "great crab"}
        ):
            return False
        if any(k in name for k in ("liquid flame", "dragon's breath", "infernal")) and (
            champion(enemy) == "blazing" or enemy_name in {"fire elemental", "newborn fire elemental", "burning fist"}
        ):
            return False
        if any(k in name for k in ("frost", "snap freeze")) and enemy_name == "frost elemental":
            return False
        if "wand" in name or "staff" in name:
            return not self.hostile_champions or magic_factor(enemy) > 0
        return True

    def menu(self, state):
        if self.wandmaker_menu and state.get('scene')=='GameScene':
            try:
                from .wandmaker_quest import menu
            except ImportError:
                from wandmaker_quest import menu
            return menu(self,state)
        if self.sell_plan and state.get('scene')=='GameScene':
            try:
                from .inventory_tactics import sale_menu
            except ImportError:
                from inventory_tactics import sale_menu
            sale=sale_menu(self,state)
            if sale:return sale
        if self.drop_plan and state["scene"] == "GameScene" and self.drop_plan["stage"]=="confirm":
            return drop_menu(self,state)
        if self.puzzle_identify_plan and state["scene"] == "GameScene":
            return identify_menu(self,state)
        if self.ghost_menu and state["scene"] == "GameScene":
            return quest_menu(self, state)
        if self.enemy_inspection:
            target, self.enemy_inspection = self.enemy_inspection, None
            texts = " ".join(state["ui"].get("texts", [])).replace("_", "").lower()
            if target["name"].lower() not in texts:
                raise Finished("blocked", "Enemy inspection title changed; refusing private-state inference")
            self.inspection_cache = dict(target, buffs={b["label"].strip().lower() for b in state["ui"]["buttons"]})
            return self.decision({"type": "back"}, "inspect: retain only publicly rendered enemy status icons")
        if self.inventory_stone_plan and state["scene"] == "GameScene":
            return inventory_stone_menu(self, state)
        if self.intuition_plan and state["scene"] == "GameScene":
            return intuition_menu(self, state)
        if self.mage_plan and state["scene"] == "GameScene":
            return mage_menu(self, state)
        if self.artifact_menu and state["scene"] == "GameScene":
            plan = self.artifact_menu
            if isinstance(plan,dict) and plan.get('kind') in {'tome','spellbook','rose','spellbook-add'}:
                try:
                    from .artifact_extensions import menu
                except ImportError:
                    from artifact_extensions import menu
                return menu(self,state,plan)
            self.artifact_menu = None
            if isinstance(plan, dict) and plan["kind"] == "feed":
                plan["steps"] += 1
                target = next((b for b in state["ui"]["buttons"] if b["label"].lower() == plan["target"]), None)
                if target:
                    return self.decision({"type": "button", "id": target["id"]}, "artifact: select budgeted seed for sandals")
                bag = next((b for b in state["ui"]["buttons"] if b["label"].lower() in {"velvet pouch", "backpack"}
                            and b["label"] not in plan["bags"]), None)
                if bag and plan["steps"] < 4:
                    plan["bags"].add(bag["label"])
                    self.artifact_menu = plan
                    return self.decision({"type": "button", "id": bag["id"]}, "artifact: find budgeted seed in observed bag")
                return self.decision({"type": "back"}, "artifact: cancel unavailable seed feeding")
            if plan == "chalice":
                import re
                text = " ".join(state["ui"].get("texts", [])).replace("_", "").lower()
                damage = re.search(r"deal\s+(\d+)-(\d+) damage", text)
                safe = damage and state["hero"]["hp"]-int(damage[2]) >= max(15, state["hero"]["max_hp"]*0.65)
                prefix = "yes, i know" if safe else "no, i changed"
                choice = next((b for b in state["ui"]["buttons"] if b["label"].lower().startswith(prefix)), None)
                if choice:
                    return self.decision({"type": "button", "id": choice["id"]}, "artifact: accept budgeted prick" if safe else "artifact: reject unsafe or unparsed prick damage")
                raise Finished("blocked", "Unsupported chalice safety confirmation")
            freeze = next((b for b in state["ui"]["buttons"] if "freeze time" in b["label"].lower()), None)
            if freeze:
                return self.decision({"type": "button", "id": freeze["id"]}, "artifact: confirm time freeze")
            raise Finished("blocked", "Unsupported hourglass choice; refusing guessed activation")
        if state["scene"] == "AlchemyScene":
            return alchemy_menu(self, state)
        if state["scene"] != "HeroSelectScene":
            return super().menu(state)
        buttons = state["ui"]["buttons"]
        checks = {b["label"].strip().lower(): b for b in buttons if "checked" in b}
        if checks:
            if not self.challenge_window_opened or set(checks) != set(CHALLENGES) \
                    or len([b for b in buttons if 'checked' in b])!=len(CHALLENGES) \
                    or any(not isinstance(c['checked'],bool) for c in checks.values()):
                raise Finished("blocked", "Unexpected challenge controls; need all nine visible checkboxes")
            for name in CHALLENGES:
                desired=name in self.enabled_challenges
                if checks[name]["checked"] is not desired:
                    self.challenges_verified=False;self.verified_challenges=()
                    return self.decision({"type": "button", "id": checks[name]["id"]}, f"challenge: {'enable' if desired else 'disable'} {name}")
            self.challenges_verified = True
            self.verified_challenges=tuple(c for c in CHALLENGES if checks[c]['checked'])
            reason='challenge: save nine visibly checked challenges' if self.rules.mode=='all-nine' else \
                'challenge: save eight enabled challenges with On a Diet visibly disabled' if self.rules.mode=='eight-without-on-diet' else \
                'challenge: save regular game with all nine challenges visibly disabled' if self.rules.mode=='regular' else \
                'challenge: save exactly configured visible challenge set'
            return self.decision({'type':'back'},reason)
        if self.challenges_verified and self.requested_seed and not self.verified_seed:
            return seed_menu(self,state)
        if state.get("modal"):
            raise Finished("blocked", "Cannot verify challenges: locked or unsupported startup dialog")
        if not any(t.strip().lower() == "mage" for t in state["ui"].get("texts", [])):
            mage = next((b for b in buttons if b["label"].lower() == "mage"), None)
            if mage:
                return self.decision({"type": "button", "id": mage["id"]}, "menu: mage")
            raise Finished("blocked", "Mage selection is unavailable")
        if not self.challenges_verified:
            challenge = next((b for b in buttons if b["label"].lower() == "challenges"), None)
            if not challenge and not self.startup_options_opened and not self.challenge_window_opened:
                options = next((b for b in buttons if b["label"].strip().lower() == "game options"), None)
                if options:
                    self.startup_options_opened = True
                    return self.decision({"type": "button", "id": options["id"]}, "challenge: open game options")
            if not challenge or self.challenge_window_opened:
                raise Finished("blocked", "Challenge verification unavailable; refusing unverified start")
            self.challenge_window_opened = True
            return self.decision({"type": "button", "id": challenge["id"]}, "challenge: inspect all nine toggles")
        return super().menu(state)

    def choose(self, state):
        if self.sell_plan and self.sell_plan['stage']=='unverified':
            self.stop_unsafe('Sale confirmation did not verify item removal and gold gain; never retry')
        if self.sell_plan and self.sell_plan['stage']=='close' and state.get('status')=='ready' and not state.get('modal'):
            self.sell_plan=None
        if state.get("scene") == "GameScene" and not self.challenges_verified:
            raise Finished("blocked", "Start through Mage selection: all nine challenges must be visibly verified" if self.rules.mode=='all-nine'
                           else 'Start through Mage selection: requested challenge checkbox states must be visibly verified')
        if state.get('scene')=='GameScene' and self.verified_challenges!=self.enabled_challenges \
                and not (self._legacy_all_nine_verification and self.rules.mode=='all-nine'):
            raise Finished('blocked','Eight-challenge configuration must be visibly verified: On a Diet off, all other challenges on'
                           if self.rules.mode=='eight-without-on-diet' else 'Configured challenge set must be exactly visibly verified')
        if state.get("scene")=="GameScene" and self.requested_seed and self.verified_seed!=self.requested_seed:
            self.stop_unsafe("Requested seed was not visibly verified before game start")
        # Policy metadata is local configuration, never inferred private game state.
        state = dict(state, policy_rules=self.rules.as_dict())
        decision = super().choose(state)
        if state.get('scene')=='GameScene':
            try:
                from .great_crab_tactics import guard_movement
            except ImportError:
                from great_crab_tactics import guard_movement
            guard_movement(self,state,decision)
        if state.get('scene')=='GameScene':
            try:
                from .trap_field_tactics import before_move
            except ImportError:
                from trap_field_tactics import before_move
            scan=before_move(self,state,decision,[o for o in state.get('objects',[]) if is_hostile(o)])
            if scan:decision=scan
        if state.get("status")=="ready" and not state.get("modal") and decision.action.get("type")=="cell" \
                and decision.action.get("cell")!=state["hero"]["cell"] \
                and not self.escape_step_allowed(state,decision.action.get("cell")) \
                and not any(is_hostile(o) and o["cell"]==decision.action["cell"] for o in state.get("objects",[])):
            self.stop_tactical("fire-route-rejected","Active fire buffer: refusing movement beside a barrier or onto ignition-prone ground")
        if state.get("scene")=="GameScene" and not any(is_hostile(o) for o in state.get("objects",[])):
            pickup=before_room_exit(self,state,decision)
            if pickup:
                decision=pickup
        if decision.intent in {Intent.LOOT,Intent.EXPLORE} and state["hero"]["hp"]<0.65*state["hero"]["max_hp"]:
            step=decision.action.get("cell")
            if step is not None and any(distance(step,e["cell"],state["map"]["width"])<=
                    (2 if champion(e)=="giant" else 4 if champion(e)=="projecting" else 1)
                    for e in self.recent_threats.values()):
                self.stop_tactical("recent-pursuit","Recent pursuit: refusing wounded loot/exploration re-entry into observed enemy reach")
        exit_cell = decision.action.get("cell")
        if decision.action.get("type") == "cell" and exit_cell != state["hero"]["cell"] \
                and not any(is_hostile(o) and o["cell"] == exit_cell for o in state.get("objects",[])):
            try:
                from .summoning_tactics import rooms, suspected_rooms
            except ImportError:
                from summoning_tactics import rooms, suspected_rooms
            w,h = state["map"]["width"],state["map"]["height"]
            fields = rooms(self.tiles,w,h) + [area for area,_ in suspected_rooms(self.tiles,self.loot,w,h)]
            tile = self.tiles.get(exit_cell,{})
            if tile.get("terrain") == 18 and tile.get("trap","").lower() == "summoning trap" \
                    or any(exit_cell in area and state["hero"]["cell"] not in area for area in fields):
                self.stop_tactical("summoning-entry","Summoning room requires remote activation from a prepared exterior choke")
        if decision.intent in {Intent.LOOT,Intent.EXPLORE,Intent.REPOSITION}:
            try:
                from .escape_commitment import reverses
            except ImportError:
                from escape_commitment import reverses
            if reverses(self,state,exit_cell):
                self.stop_tactical('escape-reversal','Preserve accepted escape route until resources improve or bounded commitment expires')
        direct_exit = state.get("status")=="ready" and decision.action.get("type")=="cell" \
            and self.tiles.get(exit_cell,{}).get("terrain") in {8,22} \
            and not any(is_hostile(o) and o["cell"]==exit_cell for o in state.get("objects",[]))
        if direct_exit and decision.intent==Intent.LOOT:
            try:
                from .mimic_tactics import suspicious_container
            except ImportError:
                from mimic_tactics import suspicious_container
            # Hero.handle picks up a fresh heap before checking transitions.
            # Honor only the existing adjacent LOOT admission, never remembered
            # stairs, exploration transit, or a batch continuing past the heap.
            if not state.get("modal") and not decision.movement_batch \
                    and not any(is_hostile(o) for o in state.get("objects",[])) \
                    and exit_cell not in self.navigation_barriers(state,Intent.LOOT) \
                    and any(o.get("cell")==exit_cell and o.get("top_item")
                            and not o.get("for_sale") and not suspicious_container(o)
                            for o in state.get("objects",[])):
                direct_exit = False
        if direct_exit and decision.intent!=Intent.DESCEND:
            self.stop_tactical("unplanned-stairs","Ordinary navigation attempted a stair transition; replan explicit descent or another route")
        if decision.intent == Intent.DESCEND or direct_exit:
            try:
                from .piranha_tactics import pending as pending_piranha_rooms
            except ImportError:
                from piranha_tactics import pending as pending_piranha_rooms
            try:
                from .room_supplies import depleted, POTIONS
            except ImportError:
                from room_supplies import depleted, POTIONS
            spent_rooms=depleted(self,state)
            for kind in sorted(spent_rooms):
                self.defer_obligations(state,[{'kind':'potion-room supply exhausted','room':kind,'potion':POTIONS[kind]}],
                    "Collected floor supply was used elsewhere; descend without room completion credit")
            if pending_piranha_rooms(self) and 'pool' not in spent_rooms:
                self.stop_gameplay('Piranha-room chest remains uncollected: seek/test this floor invisibility supply and finish verified retrieval before descending',
                                   kind="optional-work-exhausted")
            if self.unit_strategies_enabled:
                try:
                    from .priority_resources import targets as progression_targets
                    from .pickup_priority import food as priority_food
                except ImportError:
                    from priority_resources import targets as progression_targets
                    from pickup_priority import food as priority_food
                # Pickup priority also includes food. It is not a permanent
                # progression obligation: leave it to the normal strict/deferred
                # loot handling below, without weakening upgrade/strength or keys.
                if any(not priority_food(obj.get('top_item',obj))
                       for obj in progression_targets(self).values()):
                    try:
                        from .priority_resources import diagnostics
                    except ImportError:
                        from priority_resources import diagnostics
                    self.planner.report['priority_resource']=diagnostics(
                        self,state,[o for o in state.get('objects',[]) if is_hostile(o)])
                    self.stop_gameplay('Observed upgrade/strength resource remains uncollected; resolve its pickup before descending',
                                       kind="mandatory-preparation-unresolved")
            if self.unit_strategies_enabled and self.ghost_quest.get('stage') in {'reward','claiming','collect_dropped'}:
                self.stop_gameplay('Sad Ghost reward remains uncollected; return to its observed encounter area before descending',
                                   kind="mandatory-preparation-unresolved")
            try:
                from .exploration_budget import current_floor_food_work
            except ImportError:
                from exploration_budget import current_floor_food_work
            food_work=current_floor_food_work(self,state,[o for o in state.get('objects',[]) if is_hostile(o)])
            try:
                from .hunger_budget import exhausted
            except ImportError:
                from hunger_budget import exhausted
            if food_work and not exhausted(self,state):
                self.stop_gameplay('Starving: current-floor food search is unfinished; cannot descend while '
                                  f'known safe unexplored branches remain: {food_work}',kind="mandatory-preparation-unresolved")
            try:
                from .descent_potions import begin as test_before_descent
            except ImportError:
                from descent_potions import begin as test_before_descent
            testing = test_before_descent(self, state)
            if testing:
                return testing
            try:
                from .loot_completion import required_loot,missing_keys,pending_collections
            except ImportError:
                from loot_completion import required_loot,missing_keys,pending_collections
            required=required_loot(self)
            if pending_collections(self):
                self.planner.report['required_loot']=[{'cell':c,'name':o['name']} for c,o in sorted(required.items())]
                reason=('Observed loot incomplete: cannot clear or descend with uncollected items/chests; '
                                  'find matching keys or an admitted collection route. '
                                  f"Items={[(c,o['name']) for c,o in sorted(required.items())]}; "
                                  f"missing keys={sorted(missing_keys(self))}; "
                                  f"unresolved mimic/reward={sorted(self.mimic_obligations)}; "
                                  f"pending reusable/stashed items={bool(self.potion_stash or self.trap_payload_return)}")
                if self.stop_on_incomplete_loot:self.stop_gameplay(reason,kind="optional-work-exhausted")
                reason=reason.replace('cannot clear or descend with uncollected items/chests',
                                      'continuing descent with uncollected items/chests; no clear credit')
                detail={'items':[{'cell':c,'name':o['name']} for c,o in sorted(required.items())],
                        'missing_keys':sorted(missing_keys(self)),
                        'unresolved_mimic_rewards':sorted(self.mimic_obligations),
                        'pending_reusable_or_stashed':bool(self.potion_stash or self.trap_payload_return)}
                self.log_continuation_error(state,'incomplete-loot-at-descent',reason,detail)
                self.defer_obligations(state,[{'kind':'uncollected loot at descent',**detail}],
                                       'User permits descent with logged uncollected loot; not certified cleared')
                decision.reason+='; ERROR: outstanding loot logged, continuing descent without clear credit'
            pending = obligations(self,state)
            if self.trap_payload_return:
                try:
                    from .payload_workflow import workflow as payload_workflow, PayloadPhase
                except ImportError:
                    from payload_workflow import workflow as payload_workflow, PayloadPhase
                payload=payload_workflow(self)
                if payload.phase in {PayloadPhase.LANDED,PayloadPhase.UNVERIFIED}:
                    uncertain=payload.proposal if payload.phase==PayloadPhase.UNVERIFIED else None
                    self.physical_ledger.defer(payload,"Unfinished reusable payload at selected descent",uncertain)
            if self.potion_stash:
                try:
                    from .stash_workflow import workflow
                except ImportError:
                    from stash_workflow import workflow
                stash=workflow(self)
                self.physical_ledger.defer(stash,"Unfinished potion stash at selected descent",stash.pending)
            if pending:
                import json
                if self.stop_on_incomplete_loot and not self.planner.report.get("exploration_budget") and locked_room_route(self,state,[o for o in state.get("objects",[]) if is_hostile(o)]):
                    self.stop_tactical("descent-obligation","Descent deferred to finish reachable keyed room: "+json.dumps(pending))
                self.defer_obligations(state,pending,"Resource-aware descent or no actionable completion route/resource; user permits unfinished obligations")
                decision.reason+="; unresolved obligations logged and deferred"
            budget=self.planner.report.get("exploration_budget")
            if budget and any(budget.get(k,0) for k in ('frontiers_deferred','loot_deferred','doors_deferred','unreachable_deferred')):
                self.defer_obligations(state,[{"kind":"optional exploration","cell":budget["stairs"],
                    "frontiers":budget["frontiers_deferred"],"observed_loot":budget["loot_deferred"],
                    'doors':budget.get('doors_deferred',0),'unreachable':budget.get('unreachable_deferred',0)}],budget["reason"])
        if decision.intent in {Intent.RECOVER, Intent.BOSS} and decision.action["type"] == "wait":
            self.floor_recovery += 1
            if decision.controller=='preparation-and-recovery':self.natural_healing_waits+=1
        try:
            from .movement_batching import prepare as batch_movement
        except ImportError:
            from movement_batching import prepare as batch_movement
        decision=batch_movement(self,state,decision)
        return decision

    def defer_obligations(self,state,pending,reason):
        new=[]
        known={(r["depth"],r.get("branch",r["obligation"].get("branch",0)),
                r["obligation"].get("kind"),r["obligation"].get("cell")) for r in self.legacy_deferred_obligations}
        for obligation in pending:
            branch=obligation.get("branch",state.get("branch",0))
            key=(state["depth"],branch,obligation.get("kind"),obligation.get("cell"))
            if key not in known:
                record={"depth":state["depth"],"branch":branch,"status":"deferred-unfinished",
                        "obligation":dict(obligation),"reason":reason}
                self.legacy_deferred_obligations.append(record)
                new.append(record)
                known.add(key)
        if new:self.planner.report.setdefault("nonfatal_obligations",[]).extend(new)

    def log_continuation_error(self,state,kind,reason,detail=None):
        record=next((r for r in self.continuation_errors if (r['depth'],r['branch'],r['cell'],r['kind'],r['reason'])==
                     (state['depth'],state.get('branch',0),state['hero']['cell'],kind,reason)),None)
        if record is None:
            record={'severity':'error','kind':kind,'depth':state['depth'],'branch':state.get('branch',0),
                    'cell':state['hero']['cell'],'reason':reason,'detail':detail or {},'occurrences':0}
            self.continuation_errors.append(record)
        record['occurrences']+=1
        self.planner.report['continuation_error']=record
        return record

    def recover_no_safe_action(self,state,blocked):
        if self.stop_on_no_safe_action:return None
        if state.get('status')!='ready' or state.get('modal'):return None
        try:
            from .continuation import best_effort
        except ImportError:
            from continuation import best_effort
        self.planner.begin();self.update(state)
        self.log_continuation_error(state,'no-verified-safe-action',blocked.reason)
        return best_effort(self,state,[o for o in state.get('objects',[]) if is_hostile(o)])

    def update(self, state):
        previous = self.last_state
        try:
            from .potion_stash import observe_bandolier
        except ImportError:
            from potion_stash import observe_bandolier
        observe_bandolier(self,state)
        try:
            from .alchemy_tactics import observe_energy
        except ImportError:
            from alchemy_tactics import observe_energy
        observe_energy(self,previous,state)
        try:
            from .hunger_budget import observe
        except ImportError:
            from hunger_budget import observe
        observe(self,state)
        old_loot=dict(self.loot) if self.depth==state['depth'] else {}
        if self.depth != state["depth"]:
            self.floor_recovery = 0
            self.inspection_inputs = 0
            self.inspection_cache = None
            self.deferred_crystal_doors.clear()
            self.bomb_cells.clear()
            self.resolved_crystal_alternatives.clear()
            self.crystal_choice_groups.clear()
            self.unseen_damage_turns = 0
            self.unseen_damage_cell = self.last_safe_cell = None
        if state.get("status") == "ready" and not state.get("modal"):
            hero = state["hero"]
            buffs = " ".join(b["name"].lower() for b in hero.get("buffs", []))
            enemies = any(is_hostile(o) for o in state.get("objects", []))
            lost = previous and previous.get("depth") == state["depth"] and hero["hp"] < previous.get("hero",{}).get("hp",0)
            prior_buffs=" ".join(b["name"].lower() for b in (previous or {}).get("hero",{}).get("buffs",[]))
            if lost and not enemies and not any(t in buffs or t in prior_buffs for t in ("burning","poison","bleed","starving","ooze")):
                self.unseen_damage_turns = 3
                self.unseen_damage_cell = hero["cell"]
            else:
                self.unseen_damage_turns = max(0, self.unseen_damage_turns-1)
                if not enemies and not lost and not self.unseen_damage_turns:
                    self.last_safe_cell = hero["cell"]
        super().update(state)
        if self.unit_strategies_enabled:
            observed=[o for o in state.get('objects',[]) if is_hostile(o)]
            self.unit_pending_movement=None
            self.planner.report['unit_engagements']=[self.unit_strategies.describe(e) for e in observed]
            self.planner.report['unit_strategy_selection']={'status':'pending arbitration; safety/preparation may preempt'}
            try:
                from .artifact_tactics import ARTIFACT_STRATEGIES,artifact_name
            except ImportError:
                from artifact_tactics import ARTIFACT_STRATEGIES,artifact_name
            self.planner.report['artifact_strategies']=[{'name':i['name'],'strategy':ARTIFACT_STRATEGIES[artifact_name(i)]}
                for i in state.get('inventory',[]) if artifact_name(i) in ARTIFACT_STRATEGIES]
        try:
            from .hidden_doors import observe_secret_discovery
        except ImportError:
            from hidden_doors import observe_secret_discovery
        observe_secret_discovery(self,previous,state)
        try:
            from .loot_completion import remember_missing
        except ImportError:
            from loot_completion import remember_missing
        try:
            from .piranha_tactics import observe as observe_piranha_rooms
        except ImportError:
            from piranha_tactics import observe as observe_piranha_rooms
        observe_piranha_rooms(self,state)
        try:
            from .piranha_profile import observe as observe_piranha_profiles
        except ImportError:
            from piranha_profile import observe as observe_piranha_profiles
        observe_piranha_profiles(self,state,previous)
        try:
            from .protected_rewards import observe as observe_protected_rewards
        except ImportError:
            from protected_rewards import observe as observe_protected_rewards
        observe_protected_rewards(self,state)
        try:
            from .puzzle_supplies import observe_pool_entrance
        except ImportError:
            from puzzle_supplies import observe_pool_entrance
        observe_pool_entrance(self,previous,state)
        remember_missing(self,old_loot)
        if previous and previous.get("depth")==state["depth"] \
                and previous.get("hero",{}).get("cell")!=state["hero"]["cell"] \
                and any(o["name"].lower()=="crystal mimic" for o in [*previous.get("objects",[]),*state.get("objects",[])]):
            self.ambush_plan=self.doorway_hold=self.snake_door_reset=None
        self.fire_buffer={n for c,t in self.tiles.items() if fire_barrier(t)
                          for n in neighbors(c,state["map"]["width"],state["map"]["height"])}
        self.fire_spread_buffer={n for c,t in self.tiles.items()
                                 if any("fire is raging" in e.lower() for e in t.get("effects",[]))
                                 for n in neighbors(c,state["map"]["width"],state["map"]["height"])
                                 if self.tiles.get(n,{}).get("terrain") in {2,5,6,13,15,27,30}}
        observe_hunts(self,state,distance)
        if state.get("status")=="ready" and not state.get("modal"):
            seen={o["cell"]:dict(o,observations_ago=0) for o in state.get("objects",[])
                   if is_hostile(o) and not o.get("sleeping")}
            for cell,enemy in seen.items():
                if enemy["name"].lower()=="dm-100":
                    bind_threat(self,state,enemy,cell)
            self.recent_threats={c:dict(e,observations_ago=e["observations_ago"]+1)
                                 for c,e in self.recent_threats.items()
                                 if c not in seen and not self.tiles.get(c,{}).get("visible")
                                 and e["observations_ago"]<6}
            self.recent_threats.update(seen)
            # Accepted quiet inputs may have reached the release threshold
            # while the last sighting was still retained. Recheck after its
            # ordinary expiry, before route arbitration can reject progress
            # and roll this fresh observation back during tactical recovery.
            if self.unit_strategies_enabled and self.pursuit_quiet_moves >= 3 \
                    and not self.recent_threats and not self.unseen_damage_turns \
                    and not state.get("danger_cells") \
                    and previous and previous.get("depth") == state["depth"] \
                    and hero["hp"] >= previous.get("hero", {}).get("hp", hero["hp"]) \
                    and not any(t in buffs for t in ("poison", "burn", "bleed")):
                self.escape_commitment = None  # Route release, not a kill receipt.
            if not self.recent_threats and not seen:
                self.snake_route=None
                self.snake_route_inputs=0
                self.snake_route_edges.clear()
        try:
            from .keyed_rooms import observe as observe_keyed_rooms
        except ImportError:
            from keyed_rooms import observe as observe_keyed_rooms
        observe_keyed_rooms(self,state)
        try:
            from .dm100_escape import observe as observe_dm100
        except ImportError:
            from dm100_escape import observe as observe_dm100
        observe_dm100(self,state)
        self.deferred_crystal_doors.intersection_update(c for c, t in self.tiles.items() if t["terrain"] == 31)
        self.optional_locks.update(self.deferred_crystal_doors)
        observe_quest(self, state)
        try:
            from .wandmaker_quest import observe as observe_wandmaker
        except ImportError:
            from wandmaker_quest import observe as observe_wandmaker
        observe_wandmaker(self,state)
        observe_bombs(self, state, distance)
        if not any(is_hostile(o) and not o.get("sleeping") for o in state.get("objects", [])):
            prepare_containers(self, state)
        if self.rules.combat_pressure and state.get("status") == "ready" and not state.get("modal"):
            self.challenge_combat.observe(self, state, [o for o in state.get("objects", []) if is_hostile(o)], line_clear)
        elif self.unit_strategies_enabled:
            self.challenge_combat.observe_vision(self)  # Public smoke geometry also matters in regular games.

    def recovery_limit(self, state, hungry):
        try:
            from .hunger_budget import admits
        except ImportError:
            from hunger_budget import admits
        if not admits(self,state,1):return 0
        if self.unseen_damage_turns:
            return 0
        if not self.rules.scarce_recovery:
            try:
                from .recovery_economy import budget
            except ImportError:
                from recovery_economy import budget
            return budget(self,state,hungry)
        budget = 6 if hungry else 24
        if not self.food_items(state):
            budget = 0 if hungry else 12
        elif not hungry and state["hero"]["hp"]<0.9*state["hero"]["max_hp"] and suspect_container_pending(self,state):
            budget+=80
        elif not hungry and 0.8*state["hero"]["max_hp"]<=state["hero"]["hp"]<0.95*state["hero"]["max_hp"] \
                and frost_recovery_nearby(self,state,distance) \
                and any(unknown_potion(i) and "DRINK" in i.get("actions",[]) for i in state["inventory"]):
            budget+=40  # Bounded recovery for the unchanged near-full-HP frost test.
        if self.food_recovery_source!='fire' or frost_recovery_nearby(self,state,distance):
            budget=max(budget,self.food_recovery_until)
        return budget if self.floor_recovery < budget else 0

    def recovery_target(self,state):
        # Mandatory discovery requires 85% HP; ordinary 75% recovery otherwise
        # stops just short and falsely declares its health prerequisite exhausted.
        discovery_target=.85 if not self.pharmacophobia and not self.strength_identified and any(
                unknown_potion(i) and "DRINK" in i.get("actions",[]) for i in state["inventory"]) else 0
        if not self.rules.scarce_recovery:
            # A blocked mandatory fire reward still needs the unchanged 95%
            # unknown-frost test threshold. Ordinary recovery otherwise yields
            # to exploration at 65/75%, stranding that preparation prerequisite.
            # Raise the target only: the existing hunger, exposure and total
            # floor wait budget continue to admit or reject each recovery input.
            if any(unknown_potion(i) and "DRINK" in i.get("actions",[])
                   and (state["depth"],base_name(i)) not in self.puzzle_drinks
                   for i in state["inventory"]) and not any(
                       base_name(i)=="potion of frost" for i in state["inventory"]):
                try:
                    from .priority_resources import targets, NAMES
                except ImportError:
                    from priority_resources import targets, NAMES
                paths=self.paths(state)
                fires=[c for c,t in self.tiles.items() if fire_barrier(t)]
                if any(c not in paths and base_name(obj.get("top_item",obj)) in NAMES
                       and any(distance(c,f,state["map"]["width"])<=6 for f in fires)
                       for c,obj in targets(self).items()):
                    return .95
            return max(discovery_target,.9 if state['depth']%5==0 else .75 if self.food_items(state) else .65)
        if (self.food_items(state) or self.food_recovery_until>self.floor_recovery) and frost_recovery_nearby(self,state,distance) \
                and any(unknown_potion(i) and "DRINK" in i.get("actions",[]) for i in state["inventory"]):
            return 0.95
        if self.food_items(state) and suspect_container_pending(self,state):
            return 0.9
        return max(discovery_target,super().recovery_target(state))

    def conserve_descent_allowed(self, state):
        return False  # Resource-aware selection uses verified routes and explicit deferrals instead.

    def descent_counts_as_clear(self):
        # A depth transition is not proof that deferred rooms/items were completed.
        try:
            from .loot_completion import pending_collections
        except ImportError:
            from loot_completion import pending_collections
        return not pending_collections(self) and not any(r['depth']==self.depth for r in self.deferred_obligations) \
            and not any(r['depth']==self.depth for r in self.missed_loot)

    def exploration_loot_allowed(self,state,cell,paths):
        try:
            from .inventory_tactics import discarded
        except ImportError:
            from inventory_tactics import discarded
        if discarded(self,cell,self.loot.get(cell,{})):return False
        if cell in self.combat_deferred_loot:return False
        if self.strict_observed_loot:return True
        reason=exploration_pressure(self,state)
        if not reason:return True
        if food_loot(self.loot.get(cell,{})):return True
        route=self.route(paths,cell)
        # Keep short pickups; do not backtrack through the floor for speculative
        # loot while starving merely because the exit has not been found yet.
        if len(route)<=7:return True
        self.defer_obligations(state,[{'kind':'resource-deferred loot','cell':cell,
            'name':self.loot.get(cell,{}).get('name','observed chest')}],reason)
        return False

    def navigation_barriers(self,state,intent):
        forbidden={7,8,22,37} if intent!=Intent.DESCEND else {7,37}
        barriers={c for c,t in self.tiles.items() if t["terrain"] in forbidden}
        if state['hero']['cell'] not in self.completed_maze_cells and intent in {Intent.EXPLORE,Intent.LOOT,Intent.REPOSITION}:
            barriers.update(self.completed_maze_cells)
        if intent==Intent.LOOT and not self.recent_threats and state.get('status')=='ready' and not state.get('modal'):
            pos=state['hero']['cell'];width=state['map']['width']
            for obj in state.get('objects',[]):
                c=obj['cell']
                if c in barriers and self.tiles[c].get('visible') and obj.get('top_item') \
                        and not obj.get('for_sale') and distance(pos,c,width)<=1:
                    barriers.remove(c)  # Heap pickup precedes stair interaction; never a route through stairs.
        return barriers

    def walkable(self,cell,occupied=(),ignored_neutrals=(),ignored_plants=()):
        return self.escape_step_allowed(self.last_state or {},cell) \
            and super().walkable(cell,occupied,ignored_neutrals,ignored_plants)

    def escape_step_allowed(self,state,cell):
        burning=any("burning" in b["name"].lower() for b in state.get("hero",{}).get("buffs",[]))
        return cell not in self.fire_buffer and (cell not in self.fire_spread_buffer or burning)

    def search_limit(self, state, default, optional):
        try:
            from .hunger_budget import admits
        except ImportError:
            from hunger_budget import admits
        if optional and not admits(self,state,12):return 0
        try:
            from .hidden_doors import secret_search_allowed
        except ImportError:
            from hidden_doors import secret_search_allowed
        if not secret_search_allowed(state,self):
            self.planner.report['secret_search']={'status':'disabled on non-Goo boss floor; no secret-room hypothesis'}
            return 0
        # A hunger label is not exhaustion of carried food. For missing-exit
        # work only, retain the existing well-fed ceiling when a fresh public
        # forecast funds a search. Committed approaches still independently
        # require their round-trip travel plus search reserve on every step.
        buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
        if not optional and not self.rules.scarce_recovery and 'hungry' in buffs \
                and self.food_items(state) and not self.recent_threats \
                and not state.get('danger_cells') \
                and not any(is_hostile(o) for o in state.get('objects',[])) \
                and state['hero']['hp']>=.7*state['hero']['max_hp'] \
                and not any(b in buffs for b in ('starving','burn','poison','bleed','blind','vertigo','paral','root')) \
                and not any(self.tiles[c]['terrain'] in {8,22} for c in self.paths(state)):
            try:
                from .hunger_budget import forecast
            except ImportError:
                from hunger_budget import forecast
            estimate=forecast(self,state)
            if estimate and estimate['optional_turns']>=12:
                return 40
        if self.requires_key_search(state):return max(12,default)
        if not self.rules.scarce_recovery:return super().search_limit(state,default,optional)
        if optional and exploration_pressure(self,state):return 0
        if optional and not self.keys.get("golden",0) and self.food_items(state) \
                and state["hero"]["hp"]>=0.7*state["hero"]["max_hp"] \
                and any(o["name"].lower()=="locked chest" and not o.get("for_sale") for o in self.loot.values()):
            return max(4,min(default,12))  # Missing required key warrants bounded searches even when hungry.
        return min(default, 2 if optional else 12 if self.food_items(state) else 6)

    strict_observed_loot=True

    def requires_key_search(self,state):
        try:
            from .loot_completion import missing_keys
        except ImportError:
            from loot_completion import missing_keys
        return self.strict_observed_loot and bool(missing_keys(self))

    def sweep_limit(self, state):
        try:
            from .hunger_budget import admits
        except ImportError:
            from hunger_budget import admits
        if not admits(self,state,1):return 0
        if not self.rules.scarce_recovery:return super().sweep_limit(state)
        if exploration_pressure(self,state):return 0
        return 12 if self.food_items(state) else 0

    def attack_score(self, state, enemy, kind, value):
        trait = champion(enemy) if self.hostile_champions else None
        if kind == "magic":
            value *= magic_factor(enemy) if self.hostile_champions else 1
            if "mimic" in enemy["name"].lower() and (not self.hostile_champions or magic_factor(enemy)>0):
                value += 10
        elif trait in {"antimagic", "giant", "blessed"}:
            value *= {"antimagic": 0.5, "giant": 0.2, "blessed": 0.25}[trait]
        if self.swarm_intelligence and kind == "melee" and enemy["name"].lower() == "swarm of flies":
            value *= 0.3  # Splitting flies feeds Swarm Intelligence.
        if kind == "melee" and trait == "blazing" and self.tiles.get(enemy["cell"], {}).get("terrain") != 29:
            value *= 0.3
        buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
        if kind == "melee" and "lingering magic" in buffs:
            value += 1
        if self.inspection_cache and self.inspection_cache["cell"] == enemy["cell"] \
                and any("soul mark" in b for b in self.inspection_cache["buffs"]):
            if kind in {"melee", "thrown"}:
                value += 2  # Publicly inspected Warlock recovery/satiety opportunity.
        return value

    def best_attack(self, state, enemy, reserve=False, reserve_magic=False, *, allowed_kinds=None):
        if enemy["name"].lower() == "gnoll trickster":
            allowed_kinds = {"magic", "thrown"} if allowed_kinds is None else set(allowed_kinds) & {"magic", "thrown"}
            reserve = reserve_magic = False
        if not self.rules.combat_pressure:
            return super().best_attack(state,enemy,reserve,reserve_magic,allowed_kinds=allowed_kinds)
        if champion(enemy) or enemy['name'].lower() in {'sewer snake','sewer crab'}:
            reserve = reserve_magic = False
        elif enemy["name"].lower() in {"marsupial rat", "albino rat"} \
                and state["hero"]["hp"] >= (0.65 if self.challenge_combat.sight_inputs>=4 else 0.8)*state["hero"]["max_hp"] \
                and distance(state["hero"]["cell"],enemy["cell"],state["map"]["width"])==1 \
                and sum(is_hostile(o) and not o.get("sleeping") for o in state.get("objects",[]))<=1:
            reserve_magic=True
        # Retain scarce known charges for evasive/fast/champion targets, but
        # only when a healthy single-rat melee alternative already exists.
        if not champion(enemy) and enemy['name'].lower() in {'marsupial rat','albino rat'} \
                and state['hero']['hp']>=.65*state['hero']['max_hp'] \
                and distance(state['hero']['cell'],enemy['cell'],state['map']['width'])==1 \
                and sum(is_hostile(o) and not o.get('sleeping') for o in state.get('objects',[]))==1:
            known=[i for i in self.charged_magic(state) if (i.get('status') or '').split('/')[0].isdigit()]
            if known and sum(int(i['status'].split('/')[0]) for i in known)<=2:
                reserve_magic=True
                self.planner.report['dangerous_enemy_reserve']={'known_charges':sum(int(i['status'].split('/')[0]) for i in known),
                    'for':'snakes, crabs, champions; no unknown-charge estimate treated as certain'}
        return super().best_attack(state, enemy, reserve, reserve_magic,allowed_kinds=allowed_kinds)

    def attack_kind_allowed(self,state,enemy,kind):
        if enemy["name"].lower()=="great crab":
            # Shared attacks (including recovery) must not undo the quest
            # controller's refusal of the visible guard. Doorway surprise is
            # admitted separately by door_ambush, not by damage scoring.
            buffs=" ".join(b["name"].lower() for b in state["hero"].get("buffs",[]))
            if not enemy.get("sleeping") and "invisib" not in buffs:
                return False
        try:
            from .fly_tactics import physical_attack_unsafe
        except ImportError:
            from fly_tactics import physical_attack_unsafe
        return kind not in {'melee','thrown'} or not physical_attack_unsafe(self,state,enemy)

    def attack_approach_allowed(self,state,enemy):
        return self.attack_kind_allowed(state,enemy,'melee')

    def door_ambush_limit(self):
        return 3  # A successful doorway can serve another publicly seen pursuer.

    def snake_fallback_budget(self):
        return 2  # Only high-health isolated ordinary snakes after safer options fail.

    def snake_reposition(self,state,enemies):
        return seek_next_door(self,state,enemies,distance,neighbors,line_clear)

    def recover_tactical_block(self,state,blocked):
        self.planner.begin()
        self.update(state)
        observe_wand_cast(self,state)
        enemies=[o for o in state.get("objects",[]) if is_hostile(o)]
        return recover_tactic(self,state,enemies,blocked,distance,neighbors,line_clear)

    def door_ambush(self,state,enemies,targets,kind="wraith"):
        if any(e["name"].lower()=="crystal mimic" for e in targets):
            self.ambush_plan=None
            return None  # It flees and can teleport the hero; it is not a door-blockable pursuer.
        cost=self.doorway_lure_cost
        if kind!="doorway" and cost.get("depth")==state["depth"] \
                and cost.get("spent",0)>=max(3,0.2*state["hero"]["max_hp"]):
            return None  # Do not bypass an observed failed-lure budget downstream.
        action=super().door_ambush(state,enemies,targets,kind)
        if action and action.action.get('type')=='wait' and any(
                not e.get('sleeping') and reach(e)>1
                and distance(state['hero']['cell'],e['cell'],state['map']['width'])<=reach(e) for e in enemies):
            self.ambush_plan=None
            self.planner.report['doorway_first']={'status':'decline lure wait within advertised extended reach'}
            return None
        if action and kind!="doorway" and action.action.get("type")=="cell":
            step=action.action["cell"]
            moving=not any(e["cell"]==step for e in enemies)
            if moving and self.tiles.get(step,{}).get("terrain")!=29 \
                    and any(champion(e)=="blazing" and distance(step,e["cell"],state["map"]["width"])<=reach(e)
                            for e in enemies if not e.get("sleeping")):
                self.ambush_plan=None
                return None  # Legacy snake/swarm lures must not bypass the dry-fire guard.
        return action

    def retreat_preferences(self,state,enemies,candidates):
        try:
            from .escape_commitment import reverses
        except ImportError:
            from escape_commitment import reverses
        paths=self.paths(state,{e["cell"] for e in enemies})
        preference={}
        width,height=state["map"]["width"],state["map"]["height"]
        active=[e for e in enemies if not e.get("sleeping")]
        pos=state["hero"]["cell"]
        water_guard=self.tiles[pos]["terrain"]==29 and any(champion(e)=="blazing" for e in active)
        for door in paths:
            if self.tiles[door]["terrain"] not in {5,6}:
                continue
            route=self.route(paths,door)
            if 2<=len(route)<=6 and route[1] in candidates \
                    and all(self.tiles[c]["terrain"] not in {7,8,21,22,31,37,38} and c not in self.loot
                            and not self.tiles[c].get("plant") for c in route[1:]):
                step=route[1]
                # A just-left door is not a new escape destination. Do not
                # reward retracing an accepted retreat over onward ground;
                # ordinary retreat safety/scoring still decides availability.
                if reverses(self,state,step):
                    continue
                if exposure(self,state,active,step,distance,line_clear)["exposure"]:
                    continue
                if water_guard and self.tiles[step]["terrain"]!=29 \
                        and any(self.enemy_can_see(state,e,step) and distance(step,e["cell"],width)<=reach(e)+1 for e in active):
                    continue
                try:
                    from .retreat_geometry import onward_runway
                except ImportError:
                    from retreat_geometry import onward_runway
                # A doorway is not an escape destination on its own. Require
                # observed onward space beyond it, excluding the approach so
                # a return into the pursuing enemy cannot certify an exit.
                continuation=[c for c in neighbors(door,width,height) if c not in route[:-1]
                              and abs(c%width-door%width)+abs(c//width-door//width)==1
                              and self.walkable(c,{e["cell"] for e in enemies})]
                if not continuation or not onward_runway(self,state,door,route[-2],
                        {e["cell"] for e in enemies} | set(route[:-1]),active):
                    continue
                preference[route[1]]=max(preference.get(route[1],0),1/len(route))
        return preference

    def inspect_enemy(self, enemy):
        if self.inspection_inputs >= 12:
            return None
        self.inspection_inputs += 1
        self.enemy_inspection = {"name": enemy["name"], "cell": enemy["cell"]}
        return self.decision({"type": "inspect", "cell": enemy["cell"]}, "inspect: observe enemy status through ordinary inspection window")

    def combat_override(self, state, enemies):
        if self.unit_strategies_enabled:return None  # The registry has its own leaf after emergency withdrawal.
        fleeing=crystal_mimic(self,state,enemies,distance)
        if fleeing:
            return fleeing
        try:
            from .fly_tactics import escape
        except ImportError:
            from fly_tactics import escape
        fly_escape=escape(self,state,enemies,list(self.recent_threats.values()))
        if fly_escape:return fly_escape
        doorway=doorway_first(self,state,enemies,distance,neighbors,line_clear)
        if doorway:
            return doorway
        environment = trigger_trap(self, state, enemies, distance, neighbors, line_clear) or use_bomb(self, state, enemies, distance, neighbors)
        if environment:
            return environment
        mimic=fight_mimic(self,state,enemies,distance,neighbors,line_clear)
        if mimic:
            return mimic
        quest = quest_combat(self, state, enemies, distance, neighbors)
        if quest:
            return quest
        stone = choose_runestone(self, state, enemies, distance, neighbors)
        if stone:
            return stone
        if state.get("boss_health_text") or any(e["name"].lower() in self.boss_strategies for e in enemies):
            return None  # Dedicated boss arbitration stays in charge.
        if state["hero"].get("subclass", state["hero"]["name"]).lower() == "warlock" and len(enemies) == 1 \
                and state["hero"]["hp"] < 0.7*state["hero"]["max_hp"] and not self.inspection_cache \
                and distance(state["hero"]["cell"], enemies[0]["cell"], state["map"]["width"]) == 1:
            inspected = self.inspect_enemy(enemies[0])
            if inspected:
                return inspected
        spawner = next((e for e in enemies if e["name"].lower() == "demon spawner"), None)
        if spawner and state["hero"]["hp"] >= 0.7*state["hero"]["max_hp"]:
            pos, width = state["hero"]["cell"], state["map"]["width"]
            if all(e is spawner or distance(pos, e["cell"], width) > 3 for e in enemies):
                if distance(pos, spawner["cell"], width) == 1:
                    return self.cell(spawner["cell"], "room: destroy stationary demon spawner while no nearby minions threaten")
                if self.charged_magic(state):
                    action = self.best_attack(state, spawner)
                    if action:
                        action.reason = "room: suppress observed demon spawner before reinforcements"
                        return action
        return self.challenge_withdrawal(state, enemies)

    unit_strategies_enabled=True
    reserve_floor_puzzle_supplies=True

    def challenge_withdrawal(self, state, enemies):
        if not self.rules.combat_pressure:return None
        if not self.swarm_intelligence and not any(champion(e) for e in enemies):return None
        return self.challenge_combat.choose(self, state, enemies, distance, neighbors, line_clear)

    def enemy_can_see(self, state, enemy, cell):
        return enemy_line(self, enemy, cell, state["map"]["width"], line_clear)

    def emergency_transport(self, state, enemies):
        danger = set(state.get("danger_cells", []))
        for obj in state.get("objects", []):
            if obj["name"].lower() == "smoke bomb" and "tengu" in obj.get("description", "").lower():
                danger.update(c for c in self.tiles if distance(c, obj["cell"], state["map"]["width"]) <= 2)
        goo = next((e for e in enemies if e["name"].lower() == "goo"), None)
        if goo and danger:
            danger.update(c for c in self.tiles if goo_blast_reaches(goo["cell"], c, state["map"]["width"], self.tiles))
        return blink_escape(self, dict(state, danger_cells=sorted(danger)), enemies, distance, neighbors)

    def challenge_preparation(self,state,enemies):
        """Legacy API; preparation is shared, not an implicit challenge bundle."""
        return self.preparation(state,enemies)

    def preparation(self, state, enemies):
        self.artifact_cooldown = max(0, self.artifact_cooldown - 1)
        self.battery_cooldown = max(0, self.battery_cooldown - 1)
        self.stone_cooldown = max(0, self.stone_cooldown - 1)
        self.warp_cooldown = max(0, self.warp_cooldown - 1)
        if state.get("danger_cells"):
            return None
        # Accepted pursuit accounting must run even when closing fronts yield
        # preparation to emergency retreat. This only retires new unverified
        # lures; existing retreat/hold safety gates remain in charge.
        try:
            from .pursuit_budget import review_outcome
        except ImportError:
            from pursuit_budget import review_outcome
        review_outcome(self,state)
        try:
            from .multi_enemy_tactics import needs_retreat
        except ImportError:
            from multi_enemy_tactics import needs_retreat
        if needs_retreat(self, state, enemies):
            return None  # Emergency healing/control, then doorway retreat before optional setup/loot.
        if self.wandmaker_quest.get('stage') in {'return','claiming','collect_dropped'}:
            return None  # Safety/healing, then quest return before optional work.
        if self.completed_maze_cells:
            try:
                from .maze_objective import leave as leave_maze
            except ImportError:
                from maze_objective import leave as leave_maze
            exit_maze=leave_maze(self,state,enemies)
            if exit_maze:return exit_maze
        if self.well_cleanse_plan:
            try:
                from .well_cleansing import choose as cleanse_spare
            except ImportError:
                from well_cleansing import choose as cleanse_spare
            recovered=cleanse_spare(self,state,enemies)
            if recovered:return recovered
        if self.boxed_snake_escape:
            try:
                from .boxed_snake_escape import choose as snake_exit
            except ImportError:
                from boxed_snake_escape import choose as snake_exit
            bounded=snake_exit(self,state,enemies,list(self.recent_threats.values()),resume_only=True)
            if bounded:return bounded
        if self.fly_escape_plan:
            try:
                from .fly_tactics import escape
            except ImportError:
                from fly_tactics import escape
            fly_escape=escape(self,state,enemies,list(self.recent_threats.values()))
            if fly_escape:return fly_escape
        food=starving_food(self,state,enemies)
        if food:return food
        try:
            from .hunger_budget import prioritize_supply
        except ImportError:
            from hunger_budget import prioritize_supply
        supply=prioritize_supply(self,state,enemies)
        if supply:return supply
        try:
            from .freezing_food import choose as freezing
        except ImportError:
            from freezing_food import choose as freezing
        frozen=freezing(self,state,enemies)
        if frozen:return frozen
        if enemies and self.unit_strategies_enabled:
            try:
                from .chain_tactics import choose_chasm_pull
                from .artifact_tactics import artifact_name
            except ImportError:
                from chain_tactics import choose_chasm_pull
                from artifact_tactics import artifact_name
            chains=next((i for i in state['inventory'] if i.get('equipped') and not i.get('known_cursed')
                         and artifact_name(i)=='ethereal chains'),None)
            pull=choose_chasm_pull(self,state,enemies,chains)
            if pull:return pull
        for name in self.talent_priority(state):
            talent=next((t for t in state["hero"].get("talents",[]) if t["name"].lower()==name
                         and t.get("available",0)>0 and t["points"]<t["max_points"]),None)
            if talent:
                return self.decision({"type":"talent","name":talent["name"]},
                                     "talent: allocate available survival point before ordinary actions")
        transfusion=choose_transfusion(self,state,enemies,distance)
        if transfusion:
            return transfusion
        try:
            from .pursuit_budget import due, reassess
        except ImportError:
            from pursuit_budget import due, reassess
        if self.rules.combat_pressure and enemies and due(self):
            recovery=ally_warp(self,state,enemies,distance) or warp_escape(self,state,enemies,distance) \
                or use_artifact(self,state,enemies) or shield_battery(self,state,enemies)
            if recovery:return recovery
            intervention=reassess(self,state,enemies)
            if intervention:return intervention
        reset=reset_snake_door(self,state,enemies,distance,neighbors,line_clear)
        if reset:
            return reset
        held=hold_doorway(self,state,enemies,distance,neighbors,line_clear)
        if held:
            return held
        if not enemies and self.ambush_plan and self.ambush_plan.get("kind")=="doorway":
            lure=doorway_first(self,state,enemies,distance,neighbors,line_clear)
            if lure:
                return lure
        if self.unseen_damage_turns and not enemies:
            if self.ranged_plan and self.ranged_plan.get('name')=='dm-100' \
                    and self.ranged_plan.get('mode')=='cover':
                # A bolt can land on the exposed doorway even when its caster
                # leaves hero vision. Let emergency healing and the revalidated
                # doorway-bank controller run; do not reverse into its lane.
                return None
            pos = state["hero"]["cell"]
            paths = self.paths(state, {self.unseen_damage_cell})
            goals = [c for c in paths if c != pos and len(self.route(paths,c)) <= 4
                     and self.tiles[c]["terrain"] in {1,2,3,6,9,11,14,19,20,29}
                     and c not in self.loot]
            if goals:
                target = min(goals, key=lambda c: (self.tiles[c]["terrain"] != 6, c != self.last_safe_cell, len(self.route(paths,c))))
                return self.toward(state,target,"survival: seek known safe ground after unexplained HP loss",paths)
        if not enemies and self.unit_strategies_enabled and self.ghost_quest.get('stage') in {'reward','collect_dropped'}:
            return None  # Let healing/starvation and the priority reward-return leaf arbitrate before optional utility.
        if not enemies and self.great_crab_plan:
            try:
                from .great_crab_tactics import choose as continue_crab_ambush
            except ImportError:
                from great_crab_tactics import choose as continue_crab_ambush
            ambush=continue_crab_ambush(self,state,enemies)
            if ambush:return ambush
        if not enemies and self.unit_strategies_enabled:
            try:
                from .priority_resources import targets as progression_targets
            except ImportError:
                from priority_resources import targets as progression_targets
            if progression_targets(self):
                # Required loot may itself need the potion preparation that
                # started this stash. Finish its guarded drop/return workflow
                # before yielding to a fresh staging decision for that loot.
                return advance_stash(self,state,enemies,distance)
        warp = ally_warp(self, state, enemies, distance) or warp_escape(self, state, enemies, distance)
        if warp:
            return warp
        artifact = use_artifact(self, state, enemies)
        if artifact:
            return artifact
        battery = shield_battery(self, state, enemies)
        if battery:
            return battery
        try:
            from .descent_potions import advance as advance_descent_potions
        except ImportError:
            from descent_potions import advance as advance_descent_potions
        testing = advance_descent_potions(self, state)
        if testing:
            return testing
        stash=advance_stash(self,state,enemies,distance)
        if stash:
            return stash
        if enemies:
            return None
        returned=recover_trap_payload(self,state,enemies)
        if returned:
            return returned
        try:
            from .garden_tactics import choose as garden
            from .environment_tactics import clear_blocking_trap
            from .summoning_tactics import choose as prepare_summoning
            from .seed_tactics import choose_seed
            from .resource_tactics import choose_meat
        except ImportError:
            from garden_tactics import choose as garden
            from environment_tactics import clear_blocking_trap
            from summoning_tactics import choose as prepare_summoning
            from seed_tactics import choose_seed
            from resource_tactics import choose_meat
        resource=prepare_summoning(self,state,enemies) or garden(self,state,enemies) or choose_seed(self,state,enemies,distance,neighbors) \
            or choose_meat(self,state,enemies,distance,neighbors) or clear_blocking_trap(self,state,enemies,distance,neighbors)
        if resource:return resource
        try:
            from .barrier_followup import advance
        except ImportError:
            from barrier_followup import advance
        followup=advance(self,state,enemies,distance,neighbors)
        if followup:return followup
        descent=selective_descent(self,state,enemies)
        if descent:
            return descent
        buffs=" ".join(b["name"].lower() for b in state["hero"].get("buffs",[]))
        meal_key=(state["depth"],"suspect-room-meal")
        food=self.food_items(state)
        fire_recovery_key=(state["depth"],"fire-room-recovery-reserve")
        if food and state["hero"]["hp"]<0.95*state["hero"]["max_hp"] and not self.recent_threats \
                and frost_recovery_nearby(self,state,distance) \
                and any(unknown_potion(i) for i in state["inventory"]) and fire_recovery_key not in self.room_attempts \
                and not any(t in buffs for t in ("burning","poison","blind","vertigo","paral","root")):
            self.room_attempts.add(fire_recovery_key)
            self.food_recovery_until=max(self.food_recovery_until,self.floor_recovery+90)
            self.food_recovery_source='fire'
        recovery_key=(state["depth"],"surplus-recovery-meal")
        if "hungry" in buffs and sum(i.get("quantity",1) for i in food)>=2 and state["hero"]["hp"]<0.65*state["hero"]["max_hp"] \
                and (self.rules.scarce_recovery or state['hero']['hp']<.4*state['hero']['max_hp']) \
                and not self.recent_threats and recovery_key not in self.room_attempts \
                and not any(t in buffs for t in ("starving","burning","poison","blind","vertigo","paral","root")):
            self.room_attempts.add(recovery_key)
            self.food_recovery_until=self.floor_recovery+50
            self.food_recovery_source='surplus'
            return self.use(food[0],"EAT","recover: spend surplus meal to fund bounded safe healing before next encounter")
        if "hungry" in buffs and "starving" not in buffs and food and suspect_container_pending(self,state) \
                and state["hero"]["hp"]<0.9*state["hero"]["max_hp"] and meal_key not in self.room_attempts \
                and not any(t in buffs for t in ("burning","poison","blind","vertigo","paral","root")):
            self.room_attempts.add(meal_key)
            return self.use(food[0],"EAT","room: fund bounded recovery before required suspicious-container test")
        if self.ghost_quest.get("stage") in {"active","reward","collect_dropped"}:
            reward = visit_ghost(self,state,enemies,distance,neighbors)
            if reward:
                return reward
        hunt=hunt_missing_mimic(self,state,enemies,distance)
        if hunt:
            return hunt
        recharge=charge_suspect_container(self,state,enemies)
        if recharge:
            return recharge
        if self.unit_strategies_enabled:
            try:
                from .ghost_quest import prepare_ghost
            except ImportError:
                from ghost_quest import prepare_ghost
            ghost_ready=prepare_ghost(self,state,enemies)
            if ghost_ready:return ghost_ready
        if state["hero"]["hp"]>=0.7*state["hero"]["max_hp"] and not supply_demands(self,state,distance) \
                and not self.recent_threats and not any(t in buffs for t in ("burning","poison","blind","paral","vertigo","root")):
            intuition=prepare_intuition(self,state)
            if intuition:
                return intuition  # Use a safe identification window before searching into another encounter.
        search=seek_corridor_end(self,state,enemies,distance)
        if search:
            return search
        suspect=investigate_suspect_container(self,state,enemies,distance)
        if suspect:
            return suspect
        buffs = " ".join(b["name"].lower() for b in state["hero"].get("buffs", []))
        if "herbal healing" in buffs and state["hero"]["hp"] < 0.85*state["hero"]["max_hp"] \
                and self.recovery_limit(state, "hungry" in buffs) > 0 and "starving" not in buffs:
            return self.decision({"type": "wait"}, "recover: bounded sandals herbal healing", intent=Intent.RECOVER)
        if self.alchemy_plan:
            self.alchemy_plan = None  # Station interaction did not open an alchemy scene.
        if self.rules.scarce_recovery and "starving" in buffs:
            cleansing = next((i for i in state["inventory"] if base_name(i) == "potion of cleansing"
                              and "DRINK" in i.get("actions", [])), None)
            if cleansing:
                try:
                    from .room_supplies import use as use_room_supply
                except ImportError:
                    from room_supplies import use as use_room_supply
                return use_room_supply(self,cleansing,"DRINK","challenge: cleansing restores full satiety without healing poison",kind="emergency")
        if self.into_darkness and "light" not in buffs:
            torch = next((i for i in state["inventory"] if base_name(i) == "torch"
                           and "LIGHT" in i.get("actions", [])), None)
            reserve_torch=state["depth"]==1 and state["hero"]["hp"]>=0.8*state["hero"]["max_hp"] \
                and sum(i.get("quantity",1) for i in state["inventory"] if base_name(i)=="torch")==1 \
                and any(t["terrain"] in {8,22} for t in self.tiles.values()) and not suspect_container_pending(self,state) \
                and not any(fire_barrier(t) for t in self.tiles.values())
            if torch and not reserve_torch:
                return self.use(torch, "LIGHT", "challenge: light torch before exploring darkness")
        mapping = prepare_mapping(self, state)
        if mapping:
            return mapping
        if "starving" in buffs:
            if state["hero"]["hp"]>3 and not self.recent_threats:
                return approach_alchemy(self,state,urgent=True)
            return None
        if state["hero"]["hp"] < 0.55 * state["hero"]["max_hp"]:
            return None  # No optional crafting/identification detours before recovery.
        divination = next((i for i in state["inventory"] if base_name(i) == "scroll of divination"
                           and "READ" in i.get("actions", [])), None)
        if divination:
            return self.use(divination, "READ", "alchemy: identify types with divination")
        for name in ("potion of experience", "potion of divine inspiration"):
            potion = next((i for i in state["inventory"] if base_name(i) == name and "DRINK" in i.get("actions", [])), None)
            if potion:
                return self.use(potion, "DRINK", "mage: gain known experience or extra talent points before exploring")
        recharge = next((i for i in state["inventory"] if base_name(i) == "scroll of mystical energy" and "READ" in i.get("actions", [])), None)
        if recharge and "artifact recharging" not in buffs:
            empty = [i for i in state["inventory"] if i.get("equipped") and (i.get("status") or "?").split("/")[0] in {"0", "0%"}]
            if empty:
                return self.use(recharge, "READ", "alchemy: recharge exhausted equipped artifacts and trigger Inscribed Power")
        guard = next((i for i in state["inventory"] if base_name(i) == "scroll of prismatic image" and "READ" in i.get("actions", [])), None)
        if guard and "prismatic guard" not in buffs and not any(o["name"].lower() == "prismatic image" for o in state.get("objects", [])):
            return self.use(guard, "READ", "mage: establish prismatic guard for distraction and Ally Warp")
        progression = prepare_mage(self, state)
        if progression:
            return progression
        if state["depth"] in {6, 11, 16} and state["depth"] not in self.shop_visited_floors:
            return None
        return (prepare_drop(self,state,enemies,distance,neighbors)
                or prepare_supplies(self,state,enemies,distance,neighbors)
                or approach_alchemy(self, state)
                or visit_ghost(self, state, enemies, distance, neighbors)
                or awareness_well(self, state, enemies, neighbors)
                or extinguish(self, state, enemies, distance)
                or controlled_burn(self, state, enemies, distance, neighbors)
                or plan_journey(self, state, enemies, neighbors)
                or prepare_inventory_stone(self, state) or prepare_intuition(self, state))

    def escape_special_room(self, state):
        drop = recover_drop(self,state,[o for o in state.get("objects",[]) if is_hostile(o)],distance,neighbors)
        if drop:
            return drop
        probe = recover_probe(self,state,[o for o in state.get("objects",[]) if is_hostile(o)],distance,neighbors)
        if probe:
            return probe
        bomb_danger = {c for c in self.tiles if any(distance(c,b,state["map"]["width"])<=1 for b in self.bomb_cells)}
        if state["hero"]["cell"] in bomb_danger:
            enemies = [o for o in state.get("objects",[]) if is_hostile(o)]
            escape = self.retreat(state, enemies, bomb_danger)
            if escape and escape.action.get("cell") not in bomb_danger:
                escape.reason = "bomb: leave observed burning fuse blast radius"
                return escape
            self.stop_no_safe_action("Lit bomb: no verified safe step outside blast radius")
        if self.room_journey:
            action = self.room_journey.advance(self, state, [o for o in state.get("objects", []) if is_hostile(o)], neighbors)
            if action:
                return action
        return super().escape_special_room(state)

    def explore(self, state, enemies):
        try:
            from .ghost_quest import seek_quest_foe
        except ImportError:
            from ghost_quest import seek_quest_foe
        quest=seek_quest_foe(self,state,enemies)
        if quest:return quest
        choice = crystal_choice(self, state, enemies, neighbors) if state["depth"] not in {6,11,16} or state["depth"] in self.shop_visited_floors else None
        if choice:return choice
        keyed = locked_room_route(self,state,enemies) if not enemies and not self.recent_threats and not state.get('danger_cells') else None
        return keyed or super().explore(state, enemies)

    def systematic_exploration_enabled(self,state,enemies):
        # A disabled foe becoming visible must not switch frontier planners
        # and reverse the committed route. explore() still excludes every
        # enemy-occupied cell; active foes retain the existing admission.
        return self.engine=='legacy' and not any(not e.get('sleeping') for e in enemies)

    def systematic_exploration(self,state,paths,skipped):
        try:
            from .region_navigation import choose
        except ImportError:
            from region_navigation import choose
        return choose(self,state,paths,skipped)

    def frontier_cost(self,state,paths,cell):
        base=super().frontier_cost(state,paths,cell)
        if not self.swarm_intelligence:return base
        doors=[c for c,t in self.tiles.items() if t["terrain"] in {5,6} and c in paths]
        # Prefer a nearby escape anchor when routes otherwise cost about the
        # same, without repeatedly revisiting a door or skipping distant rooms.
        return base+0.75*min((min(4,distance(cell,d,state["map"]["width"])) for d in doors),default=0)

    def talent_priority(self, state):
        # Meal effects are not reduced by On Diet. Inscribed Power is the
        # current talent name (the legacy controller still says Energizing Upgrade).
        points = {t["name"].lower(): t["points"] for t in state["hero"].get("talents", [])}
        initial = []
        has_wands = any("wand of " in i["name"].lower() for i in state["inventory"])
        if points.get("backup barrier", 0) < 2:
            initial.append("backup barrier")
        if has_wands and points.get("scholar's intuition", 0) < 2:
            initial.append("scholar's intuition")
        for name in ("empowering meal", "lingering magic", "energizing meal"):
            if points.get(name, 0) < 1:
                initial.append(name)
        if has_wands and points.get("wand preservation", 0) < 1:
            initial.append("wand preservation")
        for name in ("inscribed power", "arcane vision", "shield battery"):
            if points.get(name, 0) < 1:
                initial.append(name)
        images = any(o["name"].lower() in {"mirror image", "prismatic image"} for o in state.get("objects", [])) \
            or any(b["name"].lower() == "prismatic guard" for b in state["hero"].get("buffs", []))
        if points.get("soul eater", 0) < 1:
            initial.append("soul eater")
        if images and points.get("ally warp", 0) < 1:
            initial.append("ally warp")
        if points.get("desperate power", 0) < 1:
            initial.append("desperate power")
        if images and points.get("soul siphon", 0) < 1:
            initial.append("soul siphon")
        return (*initial, "backup barrier", "empowering meal", "lingering magic", "scholar's intuition",
                "energizing meal", "inscribed power", "arcane vision", "wand preservation", "shield battery",
                "soul eater", "desperate power", "ally warp", "soul siphon",
                "excess charge", "empowered strike", "mystical charge", "heroic energy", "remote beacon", "longrange warp", "telefrag")


if __name__ == "__main__":
    try:
        from .survival_bot import main
    except ImportError:
        from survival_bot import main
    sys.exit(main())
