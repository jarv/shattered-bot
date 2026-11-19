"""Challenge risk from rendered descriptions; no private enemy timers or stats."""
from collections import deque
import re

try:
    from .combat_items import magic_score
    from .policy_decision import Intent
    from .retreat_geometry import onward_exit
except ImportError:
    from combat_items import magic_score
    from policy_decision import Intent
    from retreat_geometry import onward_exit


def champion(enemy):
    text = enemy.get("description", "").replace("_", "").lower()
    return next((k for k in ("blazing", "projecting", "antimagic", "giant", "blessed", "growing")
                  if f"{k} champion" in text), None)


def visible_shield(state):
    amounts=[]
    for buff in state["hero"].get("buffs",[]):
        if buff["name"].lower()=="barrier":
            match=re.search(r"shielding remaining:\s*(\d+)",buff.get("description", "").replace("_", "").lower())
            if match:amounts.append(int(match[1]))
    return max(amounts,default=0)


def reach(enemy):
    return {"projecting": 4, "giant": 2}.get(champion(enemy), 1)


def magic_factor(enemy):
    return {"antimagic": 0, "giant": 0.2}.get(champion(enemy), 1)


def enemy_line(p, enemy, destination, width, line_clear):
    if enemy["name"].lower() == "gnoll geomancer":
        return line_clear(enemy["cell"], destination, width, p.tiles)
    tiles = p.challenge_combat.vision_tiles if p.challenge_combat.vision_tiles is not None else p.tiles
    # Bresenham deliberately excludes the destination, so explicitly account
    # for the hero standing inside a currently observed smoke screen too.
    clear=line_clear(enemy['cell'],destination,width,tiles)
    if getattr(p,'unit_strategies_enabled',False):
        try:
            from .policy_geometry import projectile_line_clear
        except ImportError:
            from policy_geometry import projectile_line_clear
        clear=clear or projectile_line_clear(enemy['cell'],destination,width,tiles)
    return not (p.tiles.get(destination, {}).get("visible") and any(
        e.strip().lower()=='a cloud of thick black smoke is swirling here.' for e in p.tiles[destination].get("effects", []))) \
        and clear


def exposure(p, state, enemies, cell, distance, line_clear):
    width = state["map"]["width"]
    melee = ranged = pursuit = 0.0
    for enemy in enemies:
        if enemy.get("sleeping"):
            continue
        dist = distance(cell, enemy["cell"], width)
        weight = {"blazing": 1.5, "blessed": 2, "growing": 1.5}.get(champion(enemy), 1)
        if dist <= reach(enemy):
            melee += weight
        elif (enemy["name"].lower() in {"dm-100", "gnoll shaman", "dwarf warlock", "evil eye", "scorpio"}
              or getattr(p,'unit_strategies_enabled',False) and 'ranged-attacks' in p.unit_strategies.profile(enemy).capabilities) \
                and enemy_line(p, enemy, cell, width, line_clear):
            ranged += 2
        elif dist <= reach(enemy)+1 and any(t in enemy.get("description", "").lower() for t in ("extremely fast", "double speed")):
            pursuit += weight
    return {"melee": melee, "ranged": ranged, "fast_pursuit": pursuit, "exposure": melee+ranged+pursuit}


def mixed_water_escape(p,state,enemies,distance,neighbors,line_clear,remembered=()):
    """Water prevents fire, not a surrounding swarm; prefer an open zero-risk exit.

    Only current observed-position exposure is scored. Enemy movement can erase
    the gap; onward exits reduce cul-de-sac selection, not guarantee survival.
    """
    if state.get('status')!='ready' or state.get('modal') or state.get('danger_cells'):
        return None
    pos=state['hero']['cell'];w=state['map']['width'];h=state['map']['height']
    active=[e for e in enemies if not e.get('sleeping')]
    if p.tiles[pos]['terrain']!=29 or not any(champion(e)=='blazing' for e in active) \
            or sum(distance(pos,e['cell'],w)<=reach(e) for e in active)<2:
        return None
    buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
    if any(b in buffs for b in ('burning','root','paral','vertigo','poison','bleed','ooze')) \
            or p.room_journey or p.drop_plan or p.puzzle_probe or state.get('boss_health_text') \
            or any(e['name'].lower() in p.boss_strategies or 'fist' in e['name'].lower() for e in active):
        return None
    threats=list({(e['cell'],e['name']):e for e in [*remembered,*active]}.values())
    occupied={e['cell'] for e in threats}
    def allowed(c):
        return p.walkable(c,occupied) and p.tiles[c]['terrain'] not in {5,7,8,10,21,22,31,37,38} \
            and not p.tiles[c].get('plant') and c not in p.loot
    choices=[]
    for cell in neighbors(pos,w,h):
        if not allowed(cell) or exposure(p,state,threats,cell,distance,line_clear)['exposure']:
            continue
        onward=[c for c in neighbors(cell,w,h) if c!=pos and allowed(c)]
        clear=[c for c in onward if exposure(p,state,threats,c,distance,line_clear)['exposure']==0]
        if len(clear)<2:
            continue  # Do not exchange water for a known cul-de-sac.
        follow=sum(distance(cell,e['cell'],w)<=reach(e)+1 for e in active)
        choices.append(((p.tiles[cell]['terrain']!=29,-len(clear),follow,-len(onward),p.visits[cell],cell),cell,onward))
    if not choices:return None
    _,cell,onward=min(choices)
    p.ambush_plan=p.doorway_hold=p.snake_door_reset=None
    p.planner.report['mixed_water_escape']={'from':pos,'step':cell,'onward':onward,
        'stays_in_water':p.tiles[cell]['terrain']==29,
        'exposure_before':exposure(p,state,threats,pos,distance,line_clear)['exposure'],
        'exposure_next':0,'caveat':'current observed positions only; pursuers may close the gap'}
    reason='challenge: shift along water to reduce mixed pressure with onward exits' if p.tiles[cell]['terrain']==29 \
        else 'challenge: leave crowded water for observed unexposed ground with onward exits'
    return p.cell(cell,reason,intent=Intent.RETREAT)


def finish_weak_crab(p,state,enemies,distance,neighbors,line_clear):
    """Bounded admitted ranged finish, never a kill promise from a rendered bar."""
    hero=state['hero'];pos=hero['cell'];width=state['map']['width']
    if not .4<=hero['hp']/max(1,hero['max_hp'])<.7 or p.weak_crab_finish_casts>=2:return None
    if state.get('status')!='ready' or state.get('modal') or state.get('danger_cells') \
            or state.get('boss_health_text') or p.room_journey or p.drop_plan or p.puzzle_probe:return None
    buffs=' '.join(b['name'].lower() for b in hero.get('buffs',[]))
    if any(b in buffs for b in ('burning','poison','bleed','ooze','root','paral','vertigo','invisib','cloaked','magic immun')):return None
    active=[e for e in enemies if not e.get('sleeping')]
    if any(champion(e) for e in active):return None
    current=exposure(p,state,active,pos,distance,line_clear)
    if current['ranged'] or sum(distance(pos,e['cell'],width)<=reach(e) for e in active)!=1:return None
    target=next((e for e in active if e['name'].lower() in {'sewer crab','hermit crab'}
                 and distance(pos,e['cell'],width)==1 and e.get('health_bar')
                 and e['health_bar'][1]>0 and 0<e['health_bar'][0]/e['health_bar'][1]<=.25),None)
    if not target or not p.shot_clear(state,target['cell']):return None
    closed=dict(p.tiles)
    if p.tiles[pos]['terrain']==6:closed[pos]=dict(p.tiles[pos],terrain=5)
    occupied={e['cell'] for e in enemies}
    for cell in neighbors(pos,width,state['map']['height']):
        if not p.walkable(cell,occupied) or cell in p.loot or p.tiles[cell].get('plant') \
                or p.tiles[cell].get('effects') or p.tiles[cell]['terrain'] in {5,7,8,10,21,22,31,37,38}:continue
        if exposure(p,state,active,cell,distance,line_clear)['exposure']:continue
        if all(not enemy_line(p,e,cell,width,line_clear) or not line_clear(e['cell'],cell,width,closed)
               for e in active):return None  # Preserve a genuine next-step sight break.
    wands=[i for i in p.charged_magic(state) if i.get('curse_known') and not i.get('known_cursed')
           and (i.get('status') or '').split('/')[0].isdigit() and int(i['status'].split('/')[0])>0
           and not p.unknown_magic_cooldowns[i['name']] and p.target_allowed(i,target)
           and p.attack_score(state,target,'magic',magic_score(i))>0]
    if not wands:return None
    wand=max(wands,key=lambda i:p.attack_score(state,target,'magic',magic_score(i)))
    p.weak_crab_finish_casts+=1
    p.ambush_plan=p.doorway_hold=p.snake_door_reset=None
    p.planner.report['weak_crab_finish']={'target':target['cell'],'bar_fraction':target['health_bar'][0]/target['health_bar'][1],
        'known_charges_before':int(wand['status'].split('/')[0]),'attempt':p.weak_crab_finish_casts,
        'caveat':'Observed bar and eligible charge only; no guaranteed damage, kill or survival'}
    return p.use(wand,'ZAP','challenge: ranged finish of visibly weakened adjacent crab before another exposed withdrawal',target=target['cell'])


class ChallengeCombat:
    def __init__(self):
        self.depth = None
        self.sight_inputs = self.withdrawals = 0
        self.edges = deque(maxlen=12)
        self.vision_tiles = None
        self.last_withdrawal = None
        self.stalled_withdrawals = 0
        self.rat_finishes = 0
        self.water_melee_attempts = 0
        self.boxed_casts = 0
        self.water_finish_casts = 0
        self.boxed_focus_casts = 0
        self.lone_finishing_casts = 0

    def observe_vision(self,p):
        smoke = {c for c, t in p.tiles.items() if t.get("visible") and any(
            e.strip().lower()=='a cloud of thick black smoke is swirling here.' for e in t.get("effects", []))}
        self.vision_tiles = {c: ({"terrain": 4} if c in smoke else t) for c, t in p.tiles.items()} if smoke else None

    def observe(self, p, state, enemies, line_clear):
        if self.depth != state["depth"]:
            self.__init__()
            self.depth = state["depth"]
        self.observe_vision(p)
        # A conservative exposure-input count, not the hidden attraction timer.
        visible = any(not e.get("sleeping") and enemy_line(p, e, state["hero"]["cell"], state["map"]["width"], line_clear) for e in enemies)
        self.sight_inputs = min(12, self.sight_inputs+1) if visible else 0
        if not enemies:
            self.withdrawals = 0
            self.rat_finishes = 0
            self.water_melee_attempts = 0
            self.boxed_casts = 0
            self.water_finish_casts = 0
            self.boxed_focus_casts = 0
            self.lone_finishing_casts = 0
        if not visible:
            self.last_withdrawal = None
            self.stalled_withdrawals = 0

    def choose(self, p, state, enemies, distance, neighbors, line_clear):
        active = [e for e in enemies if not e.get("sleeping")]
        if not active or state.get("danger_cells"):
            return None
        pos, width = state["hero"]["cell"], state["map"]["width"]
        hp = state["hero"]["hp"] / max(1, state["hero"]["max_hp"])
        current = exposure(p, state, active, pos, distance, line_clear)
        if p.tiles[pos]["terrain"]!=29 and any(champion(e)=="blazing" and distance(pos,e["cell"],width)<=2 for e in active):
            bank=p.retreat(state,enemies,rinse=True)
            if bank and p.tiles.get(bank.action.get("cell"),{}).get("terrain")==29 \
                    and exposure(p,state,active,bank.action["cell"],distance,line_clear)["exposure"]<=current["exposure"]:
                bank.reason="challenge: stage water before attacking visible blazing champion"
                return bank
            paths=p.paths(state,{e["cell"] for e in enemies})
            banks=[]
            for cell in paths:
                route=p.route(paths,cell)
                if p.tiles[cell]["terrain"]!=29 or not 3<=len(route)<=5:
                    continue
                if any(p.tiles[c]["terrain"] in {7,8,21,22,31,37,38} or c in p.loot
                       or p.tiles[c].get("plant") for c in route[1:]):
                    continue
                step_risk=exposure(p,state,active,route[1],distance,line_clear)
                if step_risk["exposure"] and not (hp>=0.8 and len(route)<=4
                        and not step_risk["ranged"] and step_risk["exposure"]<=current["exposure"]
                        and sum(distance(route[1],e["cell"],width)<=reach(e) for e in active)<=1):
                    continue
                banks.append(cell)
            if banks:
                target=min(banks,key=lambda c:(exposure(p,state,active,p.route(paths,c)[1],distance,line_clear)["exposure"],len(p.route(paths,c))))
                return p.toward(state,target,"challenge: approach known water before dry blazing attack",paths,intent=Intent.RETREAT)
            # A healthy hero previously fell through to an adjacent dry zap
            # when the champion blocked the route to water. Health is not fire
            # protection: take a verified non-contact step before that trade.
            buffs=' '.join(b['name'].lower() for b in state['hero'].get('buffs',[]))
            if self.withdrawals<16 and not state.get('boss_health_text') \
                    and not p.room_journey and not p.drop_plan and not p.puzzle_probe \
                    and not any(b in buffs for b in ('burning','root','paral','vertigo','poison','bleed','ooze')) \
                    and any(champion(e)=='blazing' and distance(pos,e['cell'],width)<=reach(e)
                        and (not e.get('health_bar') or e['health_bar'][1]<=0
                             or e['health_bar'][0]/e['health_bar'][1]>0.35) for e in active):
                occupied={e['cell'] for e in enemies}
                def safe(c):
                    return c in paths and p.walkable(c,occupied) and c not in p.loot and not p.tiles[c].get('plant') \
                        and p.tiles[c]['terrain'] not in {5,7,8,10,21,22,31,37,38}
                exits=[]
                for step in neighbors(pos,width,state['map']['height']):
                    if not safe(step) or exposure(p,state,active,step,distance,line_clear)['exposure'] \
                            or self.edges.count((pos,step))>=2:continue
                    onward=[c for c in neighbors(step,width,state['map']['height']) if c!=pos and safe(c)]
                    if onward:exits.append((len(onward),-p.visits[step],step))
                if exits:
                    step=max(exits)[-1]
                    self.withdrawals+=1;self.edges.append((pos,step))
                    self.last_withdrawal=(state['hero']['hp'],current['exposure'])
                    p.ambush_plan=p.doorway_hold=p.snake_door_reset=None
                    p.planner.report['dry_blazing_exit']={'step':step,'exposure_before':current['exposure'],
                        'exposure_next':0,'withdrawals':self.withdrawals,
                        'caveat':'Observed positions only; not guaranteed fire prevention or survival'}
                    return p.cell(step,'challenge: leave dry blazing contact before an exposed attack',intent=Intent.RETREAT)
        if len(active)==1 and active[0]["name"].lower() in {"marsupial rat","albino rat"} \
                and not champion(active[0]) and hp>=0.8 and self.sight_inputs<=3 \
                and 1<distance(pos,active[0]["cell"],width)<=3 \
                and not state["hero"].get("buffs"):
            return p.decision({"type":"wait"},"challenge: bounded approach wait preserves magic against lone ordinary rat")
        lost_hp = False
        if self.last_withdrawal is not None:
            previous_hp, previous_exposure = self.last_withdrawal
            lost_hp = state["hero"]["hp"] < previous_hp
            self.stalled_withdrawals = self.stalled_withdrawals+1 if current["exposure"] >= previous_exposure else 0
            self.last_withdrawal = None
        empty = not any(magic_factor(e) and p.target_allowed(i, e) for e in active for i in p.charged_magic(state))
        dangerous = any(champion(e) for e in active) or len(active) >= 2
        water_guard = p.tiles[pos]["terrain"] == 29 and any(
            champion(e) == "blazing" and distance(pos,e["cell"],width) <= 2 for e in active)
        water_escape=mixed_water_escape(p,state,enemies,distance,neighbors,line_clear)
        if water_escape:return water_escape
        if water_guard and hp>=0.5 and not current["ranged"] and self.water_finish_casts<2:
            target=next((e for e in active if champion(e)=="blazing" and e.get("health_bar")
                         and e["health_bar"][1]>0 and e["health_bar"][0]/e["health_bar"][1]<=0.35
                         and distance(pos,e["cell"],width)<=1),None)
            if target:
                attack=p.best_attack(state,target)
                if attack and attack.action.get("action")=="ZAP":
                    self.water_finish_casts+=1
                    attack.reason="challenge: finish visibly weakened blazing threat from water before exposed withdrawal"
                    return attack
        if water_guard and empty and (hp>=0.65 or hp>=0.45 and len(active)==1) \
                and not current["ranged"] and self.water_melee_attempts<3 \
                and sum(distance(pos,e["cell"],width)<=reach(e) for e in active)==1:
            target=next((e for e in active if champion(e)=="blazing" and distance(pos,e["cell"],width)==1),None)
            if target:
                self.water_melee_attempts+=1
                return p.cell(target["cell"],"challenge: bounded healthy melee against lone immediate blazing threat from water")
        if water_guard and hp>=0.65 and len(active)>=2 and not current["ranged"] \
                and sum(distance(pos,e["cell"],width)<=reach(e) for e in active)<=1:
            target=next((e for e in active if champion(e)=="blazing" and distance(pos,e["cell"],width)<=reach(e)),None)
            if target:
                attack=p.best_attack(state,target)
                if attack and attack.action.get("action")=="ZAP":
                    attack.reason="challenge: suppress lone immediate blazing threat from protected water"
                    return attack
        nearby_door = any(t["terrain"] in {5,6} and distance(pos,c,width)<=6 for c,t in p.tiles.items())
        withdraw = hp < (0.7 if dangerous or empty else 0.45) or (self.sight_inputs >= 4 and len(active) >= 2) \
            or (len(active)>=2 and nearby_door)
        p.planner.report["challenge_risk"] = {**current, "visible_exposure_inputs": self.sight_inputs,
                                               "champions": [champion(e) for e in active],
                                                "stalled_withdrawals": self.stalled_withdrawals}
        if withdraw:
            finish=finish_weak_crab(p,state,enemies,distance,neighbors,line_clear)
            if finish:return finish
        if hp>=0.65 and current["melee"]<=2 and self.rat_finishes<2 and not any(champion(e) for e in active):
            wounded=[e for e in active if e["name"].lower() in {"marsupial rat","albino rat"}
                     and distance(pos,e["cell"],width)==1 and e.get("health_bar")
                      and e["health_bar"][1]>0 and e["health_bar"][0]/e["health_bar"][1]<=0.4]
            if wounded:
                enemy=min(wounded,key=lambda e:e["health_bar"][0]/e["health_bar"][1])
                action=p.best_attack(state,enemy,reserve=True,reserve_magic=True)
                if action and action.action.get("type")=="cell":
                    self.rat_finishes+=1
                    action.reason="challenge: bounded healthy melee finish preserves charges against swarm"
                    return action
        critical_reserve=0.5 if current["melee"]>=2 else 0.35
        combat_hp=(state["hero"]["hp"]+visible_shield(state))/max(1,state["hero"]["max_hp"])
        if combat_hp < critical_reserve and current["exposure"]:
            safe = p.retreat(state,active,rinse=True) if water_guard else p.retreat(state,active)
            if safe:
                step=safe.action["cell"]
                water_ok=not water_guard or p.tiles[step]["terrain"]==29 \
                    or not any(enemy_line(p,e,step,width,line_clear) for e in active) \
                    or all(distance(step,e["cell"],width)>reach(e)+1 for e in active if champion(e)=="blazing")
                if water_ok and exposure(p,state,active,step,distance,line_clear)["exposure"]==0:
                    return safe
            kind="Critical swarm" if len(active)>=2 else "Critical pursuit"
            if len(active)==1 and not champion(active[0]) and self.lone_finishing_casts<2 \
                    and active[0]["name"].lower() in {"marsupial rat","albino rat","sewer snake","gnoll scout"}:
                target=active[0]
                bar=target.get("health_bar")
                fraction=bar[0]/bar[1] if bar and bar[1]>0 else 1
                if hp>=0.25 and fraction<=0.65 or hp>=0.15 and fraction<=0.2:
                    wands=[i for i in p.charged_magic(state) if i.get("curse_known") and not i.get("known_cursed")
                           and (i.get("status") or "").split("/")[0].isdigit()
                           and p.target_allowed(i,target) and p.shot_clear(state,target["cell"])]
                    if wands:
                        self.lone_finishing_casts+=1
                        return p.use(wands[0],"ZAP","challenge: bounded known-charge finish against lone weakened pursuer without safe retreat",target=target["cell"])
            if len(active)==2 and hp>=0.35 and not current["ranged"] and self.boxed_casts<2 \
                    and all(e["name"].lower() in {"marsupial rat","albino rat","sewer snake"}
                            and (not champion(e) or champion(e)=="blazing" and p.tiles[pos]["terrain"]==29)
                            for e in active):
                targets=sorted(active,key=lambda e:(e.get("health_bar",[1,1])[0]/max(1,e.get("health_bar",[1,1])[1]),
                                                    champion(e)!="blazing",e["name"].lower()!="sewer snake"))
                for target in targets:
                    action=p.best_attack(state,target)
                    if action and action.action.get("action")=="ZAP":
                        self.boxed_casts+=1
                        action.reason="challenge: bounded charged finishing attempt against boxed pair without safe retreat"
                        return action
            p.stop_tactical("critical-pressure",kind+": no verified unexposed immediate retreat; refusing lethal attack trade")
        continuing_swarm = p.ambush_plan and p.ambush_plan.get("kind")=="swarm" and hp>=0.5
        if len(active)>=2 and (hp>=0.65 or continuing_swarm) and not any(champion(e) for e in active) \
                and all(e["name"].lower() in {"marsupial rat","albino rat","sewer snake"} for e in active):
            ambush=p.door_ambush(state,enemies,active,kind="swarm")
            if ambush:
                cell=ambush.action.get("cell",pos)
                if any(e["cell"]==cell for e in active) or exposure(p,state,active,cell,distance,line_clear)["exposure"]<=current["exposure"]:
                    return ambush
                p.ambush_plan=None
        if len(active) >= 2 and (hp >= 0.5 or not current["melee"]):
            snakes = [e for e in active if e["name"].lower() == "sewer snake"
                      and distance(pos, e["cell"], width) <= 2 and p.shot_clear(state, e["cell"])]
            for enemy in sorted(snakes, key=lambda e: distance(pos, e["cell"], width)):
                action = p.best_attack(state, enemy)
                if action and action.action.get("action") == "ZAP":
                    action.reason = "challenge: suppress nearby evasive snake before prolonged swarm funnel"
                    return action
        if hp>=0.5 and current["melee"]>=2 and len(active)<=3 \
                and all(not champion(e) and e["name"].lower() in {"marsupial rat","albino rat"} for e in active) \
                and self.boxed_focus_casts<2:
            escape=p.retreat(state,enemies)
            weak=any(e.get("health_bar") and e["health_bar"][1]>0 and e["health_bar"][0]/e["health_bar"][1]<=0.4 for e in active)
            focus=escape is None or weak and exposure(p,state,active,escape.action["cell"],distance,line_clear)["exposure"]>0
            targets=sorted(active,key=lambda e:e.get("health_bar",[1,1])[0]/max(1,e.get("health_bar",[1,1])[1]))
            for enemy in targets if focus else []:
                action=p.best_attack(state,enemy)
                if action and action.action.get("action")=="ZAP":
                    self.boxed_focus_casts+=1
                    action.reason="challenge: charged focus against boxed ordinary rat group before more withdrawal damage"
                    return action
        if current["melee"] and (lost_hp or self.stalled_withdrawals >= 2):
            # Judge the *observed result* of fleeing, not separation from static
            # enemy positions at a distant route endpoint. No kill guarantees:
            # rendered health bars only prioritize visibly wounded pursuers.
            options = []
            try:
                from .incoming_damage import priority as incoming_priority
            except ImportError:
                from incoming_damage import priority as incoming_priority
            prefer_crab=p.pursuit_retreat_moves>=2 and not any(champion(e) for e in active)
            for enemy in active:
                if distance(pos, enemy["cell"], width) > reach(enemy) or not p.shot_clear(state, enemy["cell"]):
                    continue
                if enemy["name"].lower() in {"goo", "tengu", "dm-300", "king of dwarves", "yog-dzewa", "demon spawner"} or "fist" in enemy["name"].lower():
                    continue  # Boss immunity/phase arbitration remains separate.
                bar = enemy.get("health_bar")
                fraction = bar[0]/bar[1] if bar and bar[1] > 0 else 1
                for wand in p.charged_magic(state):
                    if not p.target_allowed(wand, enemy):
                        continue
                    score = p.attack_score(state, enemy, "magic", magic_score(wand))
                    if score > 0:
                        options.append(((-incoming_priority(p,state,active,enemy),fraction>0.35, enemy["name"].lower()!="sewer snake",
                            prefer_crab and enemy['name'].lower() not in {'sewer crab','hermit crab'},
                            fraction, -score, enemy["cell"]), wand, enemy))
            if options:
                _, wand, enemy = min(options, key=lambda option: option[0])
                p.planner.report['failing_withdrawal_target']={'cell':enemy['cell'],'name':enemy['name'],
                    'accepted_retreats':p.pursuit_retreat_moves,
                    'fast_crab_priority':prefer_crab and enemy['name'].lower() in {'sewer crab','hermit crab'},
                    'caveat':'Reorders an already-admitted cast; weak finishes and snake priority remain, no guaranteed kill'}
                self.stalled_withdrawals = 0
                return p.use(wand, "ZAP", "challenge: failing withdrawal; use charged magic on visible pursuer", target=enemy["cell"])
            if len(active) == 1 and hp >= 0.5 and not champion(active[0]) \
                    and distance(pos, active[0]["cell"], width) == 1 \
                    and "extremely fast" in active[0].get("description", "").lower():
                action = p.best_attack(state, active[0])
                if action:
                    self.stalled_withdrawals = 0
                    action.reason = "challenge: fight lone faster pursuer after failed retreat while health permits"
                    return action
        for enemy in active:
            bar = enemy.get("health_bar")
            if champion(enemy) == "blazing" and bar and bar[1] > 0 and bar[0]/bar[1] <= 0.35 \
                    and distance(pos, enemy["cell"], width) == 1 and p.tiles[pos]["terrain"] != 29:
                occupied = {e["cell"] for e in enemies}
                banks = [c for c in neighbors(pos, width, state["map"]["height"]) if p.walkable(c, occupied)
                         and p.tiles[c]["terrain"] not in {5,7,8,22,37} and c not in p.loot
                         and (p.tiles[c]["terrain"] == 29 or distance(c, enemy["cell"], width) >= 2
                              and not enemy_line(p,enemy,c,width,line_clear))
                         and exposure(p, state, active, c, distance, line_clear)["exposure"] <= current["exposure"]]
                if banks and self.withdrawals < 16:
                    step = min(banks, key=lambda c: (p.tiles[c]["terrain"] != 29, p.visits[c]))
                    self.withdrawals += 1
                    return p.cell(step, "challenge: leave blazing champion's death-fire radius before finishing",intent=Intent.RETREAT)
        if hp >= 0.5 and current["melee"]<=1 and all(not champion(e) and e["name"].lower() in {"marsupial rat", "albino rat"} for e in active):
            adjacent = [e for e in active if distance(pos,e["cell"],width)==1]
            if adjacent and (lost_hp or self.sight_inputs >= 4):
                enemy = min(adjacent,key=lambda e: (e.get("health_bar",[1,1])[0]/max(1,e.get("health_bar",[1,1])[1])))
                bar=enemy.get("health_bar")
                near_finish=bar and bar[1]>0 and bar[0]/bar[1]<=0.35
                reserve=hp>=0.8 or bool(near_finish and self.rat_finishes<2)
                action = p.best_attack(state,enemy,reserve=reserve,reserve_magic=reserve)
                if action:
                    if action.action.get("type")=="cell":self.rat_finishes+=1
                    action.reason = "challenge: finish ordinary adjacent rat instead of prolonged damaging pursuit"
                    return action
        ranged_champions = [e for e in active if reach(e) > 1
                            and 1 < distance(pos, e["cell"], width) <= reach(e)
                            and p.shot_clear(state, e["cell"])]
        if ranged_champions and not empty:
            # The legacy funnel treats all ordinary names as adjacency-only.
            # A projecting snake can hit while we reposition or zap its escort.
            enemy = min(ranged_champions, key=lambda e: (e["name"].lower() != "sewer snake", distance(pos, e["cell"], width)))
            action = p.best_attack(state, enemy)
            if action and action.action.get("action") == "ZAP":
                action.reason = "challenge: suppress extra-reach champion before ordinary funneling"
                return action
        if not withdraw:
            growing = next((e for e in active if champion(e) == "growing" and p.shot_clear(state, e["cell"])), None)
            if growing:
                return p.best_attack(state, growing)
            return None
        if len(active)==1 and active[0]["name"].lower() in {"marsupial rat","albino rat"} \
                and not champion(active[0]) and empty and hp>=0.35:
            ambush=p.door_ambush(state,enemies,active,kind="rat")
            if ambush:
                cell=ambush.action.get("cell",pos)
                if hp>=0.5 or exposure(p,state,active,cell,distance,line_clear)["exposure"]==0:
                    return ambush
                p.ambush_plan=None
        if len(active)==1 and active[0]["name"].lower()=="sewer snake" and not champion(active[0]) \
                and empty and hp>=0.65 and distance(pos,active[0]["cell"],width)==1:
            enemy=active[0]
            bar=enemy.get("health_bar")
            if bar and bar[1]>0 and bar[0]/bar[1]<=0.35 \
                    and p.snake_melee_attempts[(enemy["cell"],enemy["name"])]<4:
                buffs=" ".join(b["name"].lower() for b in state["hero"].get("buffs",[]))
                return p.snake_combat(state,enemies,buffs)
        if len(active)==1 and active[0]["name"].lower()=="sewer snake" and not champion(active[0]) and hp>=0.35:
            ambush=p.door_ambush(state,enemies,active,kind="snake")
            if ambush:
                cell=ambush.action.get("cell",pos)
                if hp>=0.5 or exposure(p,state,active,cell,distance,line_clear)["exposure"]==0:
                    return ambush
                p.ambush_plan=None
        paths = p.paths(state, {o["cell"] for o in state.get("objects", [])})
        door_preference=p.retreat_preferences(state,enemies,list(neighbors(pos,width,state["map"]["height"])))
        candidates = []
        for destination in paths:
            route = p.route(paths, destination)
            if not 2 <= len(route) <= 7:
                continue
            step = route[1]
            if not onward_exit(p,state,step,pos,{o['cell'] for o in state.get('objects',[])},active):
                continue  # Do not let a single pursuer seal the only known exit.
            if any(p.tiles[c]["terrain"] in {7, 8, 21, 22, 31, 37, 38}
                   or c in p.loot or p.tiles[c].get("plant") for c in route[1:]):
                continue
            risk = exposure(p, state, active, step, distance, line_clear)
            landing = exposure(p, state, active, destination, distance, line_clear)
            if water_guard and p.tiles[step]["terrain"] != 29:
                # One ordinary step by a pursuer can erase the apparent gap.
                # Preserve extinguishing ground unless dry escape is beyond
                # follow-up reach or breaks every currently observed sightline.
                immediate_cover = not any(enemy_line(p,e,step,width,line_clear) for e in active)
                follow_up_clear = all(distance(step,e["cell"],width) > reach(e)+1 for e in active if champion(e)=="blazing")
                if not immediate_cover and not follow_up_clear:
                    continue
            if risk["exposure"] > current["exposure"] or risk["ranged"] > current["ranged"]:
                continue
            if empty and (lost_hp or self.stalled_withdrawals >= 2) \
                    and risk["exposure"] >= current["exposure"] \
                    and any(enemy_line(p,e,step,width,line_clear) for e in active):
                continue
            if empty and hp < 0.5 and self.stalled_withdrawals >= 2 \
                    and risk["exposure"] >= current["exposure"] \
                    and any(enemy_line(p,e,step,width,line_clear) for e in active):
                continue  # A distant route endpoint is not a next-turn escape.
            unseen = not any(enemy_line(p, e, destination, width, line_clear) for e in active)
            separation = min(distance(destination, e["cell"], width)-reach(e) for e in active)
            if landing["exposure"] >= current["exposure"] and not unseen:
                continue
            step_unseen = not any(enemy_line(p,e,step,width,line_clear) for e in active)
            step_gap = min(distance(step,e["cell"],width)-reach(e) for e in active)
            score = 8*step_unseen + 5*unseen + 3*step_gap + 0.5*separation - 3*risk["exposure"] - len(route)*0.2
            if any(champion(e)=="blazing" for e in active):
                score += 10*(p.tiles[step]["terrain"]==29)
            door_steps = [i for i,c in enumerate(route[1:],1) if p.tiles[c]["terrain"] in {5,6} and i <= 6]
            if door_steps:
                score += (24 if len(active) >= 2 else 6) / min(door_steps)
            score -= 5*self.edges.count((step, pos))
            score -= 3*self.edges.count((pos, step))
            candidates.append((bool(door_preference.get(step)),score+20*door_preference.get(step,0),step))
        if candidates and self.withdrawals < 16:
            step = max(candidates)[-1]
            self.withdrawals += 1
            self.edges.append((pos, step))
            self.last_withdrawal = (state["hero"]["hp"], current["exposure"])
            return p.cell(step, "challenge: break swarm vision and preserve escape route",intent=Intent.RETREAT)
        if empty and hp < 0.35:
            p.stop_tactical("exhausted-combat","Exhausted magic at critical HP: no bounded lower-exposure withdrawal; refusing fatal melee")
        if water_guard:
            target = next(e for e in active if champion(e) == "blazing")
            action = p.best_attack(state,target)
            if action and (action.action.get("action") == "ZAP" or len(active) == 1 and hp >= 0.5):
                action.reason = "challenge: retain water protection against blazing pursuit"
                return action
            p.planner.report["challenge_blocker"]={"kind":"water-pinned mixed pursuit",
                "active_foes":len(active),"hp":state["hero"]["hp"],"risk":current,
                "charged_offensive_wands":len(p.charged_magic(state)),"withdrawals":self.withdrawals}
            p.stop_tactical("water-pinned","Blazing pursuit: no verified water-preserving retreat or safe dry sight break")
        return None
