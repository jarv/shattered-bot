"""Conservative sole-visible-exposure loss estimates, never hidden enemy stats."""
try:
    from .challenge_combat import champion,reach
    from .policy_geometry import distance
except ImportError:
    from challenge_combat import champion,reach
    from policy_geometry import distance


def key(enemy):
    return enemy['name'].lower(),champion(enemy)


def observe(p,before,after):
    try:
        from .survival_policy import is_hostile
    except ImportError:
        from survival_policy import is_hostile
    if before.get('depth')!=after.get('depth') or before.get('branch',0)!=after.get('branch',0):return
    if not before.get('hero') or not after.get('hero') or after.get('status')!='ready':return
    loss=before['hero']['hp']-after['hero']['hp']
    elapsed=[s.get('evaluation_stats',{}).get('elapsed_turns') for s in (before,after)]
    if loss<=0 or None in elapsed or not 0<elapsed[1]-elapsed[0]<=1.5:return
    sources=[]
    for s in (before,after):
        buffs=' '.join(b['name'].lower() for b in s['hero'].get('buffs',[]))
        if any(b in buffs for b in ('burning','poison','bleed','ooze','starving','corrosion')) or s.get('danger_cells'):return
        tile=next((t for t in s.get('map',{}).get('cells',[]) if t['cell']==s['hero']['cell']),{})
        if tile.get('effects') or tile.get('trap'):return
        candidates=[e for e in s.get('objects',[]) if is_hostile(e) and not e.get('sleeping')
                    and distance(s['hero']['cell'],e['cell'],s['map']['width'])<=reach(e)]
        if len(candidates)!=1:return  # Never distribute mixed-swarm damage across enemies.
        sources.append(candidates[0])
    if key(sources[0])!=key(sources[1]):return
    visible={o['cell'] for o in before.get('objects',[]) if is_hostile(o)}
    if any(c not in visible for c in p.recent_threats):return
    sample=p.incoming_damage_samples.setdefault(key(sources[0]),{'count':0,'hp_loss':0})
    sample['count']+=1;sample['hp_loss']+=loss
    return {'enemy':sources[0]['name'],'champion':champion(sources[0]),'observed_hp_loss':loss,
            'samples':sample['count'],'caveat':'Sole visible exposure estimate; unseen sources/healing can confound it. Not true enemy damage.'}


def priority(p,state,enemies,enemy):
    active=[e for e in enemies if not e.get('sleeping')]
    threats=[e for e in active if distance(state['hero']['cell'],e['cell'],state['map']['width'])<=reach(e)]
    if len(threats)<2 or enemy not in threats:return 0
    if distance(state['hero']['cell'],enemy['cell'],state['map']['width'])>1 and not p.shot_clear(state,enemy['cell']):return 0
    if not p.attack_kind_allowed(state,enemy,'melee'):
        try:
            from .combat_items import magic_score
        except ImportError:
            from combat_items import magic_score
        if not p.shot_clear(state,enemy['cell']) or not any(
                magic_score(i)>0 and p.target_allowed(i,enemy) for i in p.charged_magic(state)):
            return 0  # Do not promote an unattackable fly over an admitted target.
    sample=p.incoming_damage_samples.get(key(enemy),{})
    if sample.get('count',0)<2:return 0
    score=sample['hp_loss']/sample['count']
    p.planner.report.setdefault('incoming_damage_priority',{})[str(key(enemy))]={
        'mean_observed_hp_loss':score,'samples':sample['count'],
        'caveat':'Prioritizes admitted targets only; unknown and mixed-source damage not attributed'}
    return score
