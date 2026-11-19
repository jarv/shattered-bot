"""Fill empty ghost slots through observed outfit UI; never strip hero/ghost gear."""
import re
try:
    from .combat_items import stats,physical_score,known_cursed
    from .inventory_tactics import inferior,title,quiet
    from .artifact_tactics import artifact_name
    from .policy_decision import Finished
except ImportError:
    from combat_items import stats,physical_score,known_cursed
    from inventory_tactics import inferior,title,quiet
    from artifact_tactics import artifact_name
    from policy_decision import Finished


def rose_available(state):
    return any(artifact_name(i)=='dried rose' and i.get('equipped') and i.get('curse_known')
               and not known_cursed(i) and 'OUTFIT' in i.get('actions',[]) for i in state['inventory'])


def spares(state,strength=100):
    result=[]
    for i in state['inventory']:
        v=stats(i)
        if not v or v[0] not in {'armor','melee'} or i.get('equipped') or not i.get('identified') \
                or not i.get('curse_known') or known_cursed(i) or v[2]>strength:continue
        text=(i['name']+' '+i.get('description','')).lower()
        if any(t in text for t in ('unique','seal','staff','quest','pickaxe','boomerang')):continue
        if sum(title(j)==title(i) for j in state['inventory'])!=1:continue
        # Spare melee is useful when the Mage keeps the unique staff. Armor
        # must be demonstrably inferior, so we do not surrender a hero upgrade.
        staff=any(j.get('equipped') and 'IMBUE' in j.get('actions',[]) for j in state['inventory'])
        if inferior(state,i) or v[0]=='melee' and staff:result.append(i)
    return result


def choose(p,state,enemies):
    if not quiet(p,state,enemies) or not rose_available(state):return None
    if state['hero']['hp']<.7*state['hero']['max_hp']:return None
    available=[i for i in spares(state) if title(i) not in p.rose_outfit_attempts]
    if not available:return None
    p.artifact_menu={'kind':'rose','stage':'slots','steps':0,'bags':[]}
    rose=next(i for i in state['inventory'] if artifact_name(i)=='dried rose' and i.get('equipped'))
    return p.use(rose,'OUTFIT','artifact: inspect ghost strength and empty slots for spare equipment')


def menu(p,state,plan):
    plan['steps']+=1
    if plan['steps']>12:raise Finished('blocked','Rose outfitting exceeded bounded observed UI workflow')
    buttons=[b for b in state['ui'].get('buttons',[]) if b.get('enabled',True)]
    label=lambda b:b.get('label','').replace('_','').strip().lower()
    text=' '.join(state['ui'].get('texts',[])).replace('_','').lower()
    if plan['stage']=='close':
        if state.get('status')=='ready' and not state.get('modal'):
            p.artifact_menu=None
            return None
        return p.decision({'type':'back'},'artifact: close completed ghost outfitting')
    if plan['stage']=='verify':
        slot=[b for b in buttons if label(b)==plan['name']]
        gone=not any(title(i)==plan['name'] for i in state['inventory'])
        if len(slot)==1 and gone and "ghost's equipment" in text:
            p.planner.report['rose_outfit']={'name':plan['name'],'slot':plan['slot'],'confirmed':True,
                'evidence':'Matching occupied ghost slot and item absent from hero inventory'}
            plan['stage']='slots'
        else:
            plan['stage']='close'
            p.planner.report['rose_outfit']={'name':plan['name'],'confirmed':False,
                'qualification':'No repeated selection or assumed equipment transfer'}
            return p.decision({'type':'back'},'artifact: close unconfirmed ghost outfit; no retry')
    if plan['stage']=='slots':
        match=re.search(r'ghost can currently equip items requiring up to\s+(\d+)\s+strength',text)
        if "ghost's equipment" not in text or not match:
            raise Finished('blocked','Rose UI lacks understood public ghost strength and equipment title')
        strength=int(match[1])
        for kind,slot in (('melee','weapon'),('armor','armor')):
            empty=[b for b in buttons if label(b)=='empty '+slot+' slot']
            choices=[i for i in spares(state,strength) if stats(i)[0]==kind and title(i) not in p.rose_outfit_attempts]
            if len(empty)==1 and choices:
                item=max(choices,key=lambda i:physical_score(i,strength))
                plan.update(stage='select',name=title(item),slot=slot,strength=strength)
                p.rose_outfit_attempts.add(title(item))
                return p.decision({'type':'button','id':empty[0]['id']},'artifact: open observed empty ghost '+slot+' slot')
        p.rose_outfit_attempts.update(title(i) for i in spares(state))
        plan['stage']='close'
        return p.decision({'type':'back'},'artifact: retain occupied ghost slots and unsuitable hero spares')
    if plan['stage']=='select':
        item=next((i for i in spares(state,plan['strength']) if title(i)==plan['name']),None)
        selected=[b for b in buttons if label(b)==plan['name']]
        prompt='select a weapon' if plan['slot']=='weapon' else 'select an armor'
        if item and prompt in text and len(selected)==1:
            plan['stage']='verify'
            return p.decision({'type':'button','id':selected[0]['id']},'artifact: give verified spare to ghost; check actual slot')
        bag=next((b for b in buttons if label(b)=='backpack' and 'backpack' not in plan['bags']),None)
        if item and bag and prompt in text:
            plan['bags'].append('backpack')
            return p.decision({'type':'button','id':bag['id']},'artifact: locate ghost spare in observed backpack')
        plan['stage']='close'
        return p.decision({'type':'back'},'artifact: cancel changed or ambiguous ghost spare selection')
    raise Finished('blocked','Unsupported Rose outfit stage')
