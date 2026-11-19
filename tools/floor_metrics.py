"""Own-player per-floor accounting from accepted public observations only."""
from collections import Counter
import re


def snapshot(state):
    result={k:state[k] for k in ('depth','branch','hero','evaluation_stats','inventory','keys','objects') if k in state}
    if 'ui' in state:result['ui']={'texts':list(state['ui'].get('texts',[]))}
    return result


def name(item):
    return re.sub(r' x\d+$','',item['name'].lower())


def inventory(state):
    counts=Counter()
    for i in state.get('inventory',[]):counts[name(i)]+=i.get('quantity',1)
    return counts


class FloorMetrics:
    def __init__(self):
        self.floors={};self.last=None;self.clock=None;self.xp=None;self.dropped=Counter()

    def _floor(self,state):
        key=(state.get('depth'),state.get('branch',0)) if 'hero' in state else self.last
        if key is None or key[0] is None:return None
        self.last=key
        if key not in self.floors:
            self.floors[key]={'depth':key[0],'branch':key[1],'accepted_inputs':0,'turns':0,
                'turns_available':False,'observed_hp_loss':0,'observed_hp_recovery':0,
                 'experience_gained':0,'experience_available':False,'experience_gaps':0,
                'confirmed_journal_pickups':Counter(),'journal_evidence_available':False,
                'levels_gained':0,'gold_gained':0,'confirmed_ground_pickups':Counter(),
                'inventory_additions':Counter(),'retrieved_drops':Counter(),
                'journal_keys_acquired':Counter(),'inventory_gaps':0,'damage_events':[],
                'hp_observation_gaps':0,'descended_from':False,
                'entry_level':state.get('hero',{}).get('level'),'exit_level':state.get('hero',{}).get('level')}
        return self.floors[key]

    def accept(self,before,action,after,index=None,reason=''):
        f=self._floor(before)
        if f is None:
            # Starting gear/XP is baseline, never a floor pickup.
            self._floor(after)
            self.clock=after.get('evaluation_stats',{}).get('elapsed_turns')
            self.xp=self._xp(after)
            return
        f['accepted_inputs']+=1
        if 'ui' in before and 'ui' in after:
            try:
                from .collection_evidence import journal_pickup
            except ImportError:
                from collection_evidence import journal_pickup
            f['journal_evidence_available']=True
            journal=journal_pickup(before,action,after)
            if journal:f['confirmed_journal_pickups'][journal]+=1
        bh,ah=before.get('hero',{}),after.get('hero',{})
        stats=after.get('evaluation_stats',{})
        clock=stats.get('elapsed_turns')
        if self.clock is None:self.clock=before.get('evaluation_stats',{}).get('elapsed_turns')
        if clock is not None:
            if self.clock is not None and clock>=self.clock:
                f['turns']+=clock-self.clock;f['turns_available']=True
            self.clock=clock
        xp=self._xp(after)
        if self.xp is None:self.xp=self._xp(before)
        if xp is not None:
            if self.xp is not None:
                level,amount,threshold=self.xp
                dl=xp[0]-level
                f['levels_gained']+=max(0,dl)
                gain=xp[1]-amount if dl==0 else threshold-amount+xp[1] if dl==1 else None
                if gain is not None and gain>=0:
                    f['experience_gained']+=gain;f['experience_available']=True
                else:f['experience_gaps']+=1
            self.xp=xp
        if bh and ah:
            loss=max(0,bh['hp']-ah['hp']);f['observed_hp_loss']+=loss
            f['observed_hp_recovery']+=max(0,ah['hp']-bh['hp'])
            if loss:f['damage_events'].append({'index':index,'hp_before':bh['hp'],'hp_after':ah['hp'],
                'loss':loss,'cell':bh.get('cell'),'reason':reason})
            f['gold_gained']+=max(0,ah.get('gold',0)-bh.get('gold',0))
            f['exit_level']=ah.get('level')
            if after.get('depth',0)>before.get('depth',0):f['descended_from']=True
        else:f['hp_observation_gaps']+=1
        if 'inventory' in before and 'inventory' in after:
            old,new=inventory(before),inventory(after)
            # A rename/identification is not a newly acquired item. Only count
            # increases in carried units, and retain their uncertainty/category.
            budget=max(0,sum(new.values())-sum(old.values()))
            increases=new-old
            cell=before.get('hero',{}).get('cell')
            key=(*self.last,cell)
            selected=next((i for i in before['inventory'] if i.get('id')==action.get('id')),None)
            if action.get('type')=='item' and action.get('action') in {'DROP','THROW'} and selected:
                removed=max(0,old[name(selected)]-new[name(selected)])
                if action['action']=='DROP':self.dropped[(*key,name(selected))]+=removed
            target=action.get('cell') if action.get('type')=='cell' else None
            ground={name(o.get('top_item',o)) for o in before.get('objects',[])
                    if o.get('cell')==target and o.get('top_item') and not o.get('for_sale')}
            for item,quantity in sorted(increases.items(),key=lambda x:x[0] not in ground):
                quantity=min(quantity,budget);budget-=quantity
                if quantity<=0:continue
                f['inventory_additions'][item]+=quantity
                dropkey=(*self.last,target,item)
                returned=min(quantity,self.dropped[dropkey]) if target is not None else 0
                direct_returned=returned
                if target is not None and item in {'frozen carpaccio','chargrilled meat'} and returned<quantity:
                    rawkey=(*self.last,target,'mystery meat')
                    processed=min(quantity-returned,self.dropped[rawkey])
                    self.dropped[rawkey]-=processed;returned+=processed
                if returned:
                    f['retrieved_drops'][item]+=returned;self.dropped[dropkey]-=direct_returned
                if item in ground:f['confirmed_ground_pickups'][item]+=quantity-returned
        elif 'hero' in before or 'hero' in after:f['inventory_gaps']+=1
        oldkeys=Counter({(i['name'].lower(),i['depth']):i['quantity'] for i in before.get('keys',[])})
        newkeys=Counter({(i['name'].lower(),i['depth']):i['quantity'] for i in after.get('keys',[])})
        if 'keys' in before and 'keys' in after:
            for (item,depth),quantity in (newkeys-oldkeys).items():f['journal_keys_acquired'][f'{item} (floor {depth})']+=quantity
        if 'hero' in after:self._floor(after)

    @staticmethod
    def _xp(state):
        stats=state.get('evaluation_stats',{});hero=state.get('hero',{})
        if all(k in stats for k in ('experience','experience_to_level')) and 'level' in hero:
            return hero['level'],stats['experience'],stats['experience_to_level']

    def report(self):
        floors=[]
        for _,original in sorted(self.floors.items()):
            f=dict(original)
            if not f['turns_available']:f['turns']=None
            if not f['experience_available']:f['experience_gained']=None
            f['experience_complete']=f['experience_available'] and not f['experience_gaps']
            f['confirmed_ground_pickup_units']=sum(f['confirmed_ground_pickups'].values())
            floors.append(f)
        return {'schema':1,'floors':floors,'definitions':{
            'turns':'Cumulative own-run elapsed game time, not API inputs; transition interval attributed to departing floor.',
            'observed_hp_loss':'Sum of positive HP deltas between accepted observations; lower bound on gross HP damage (same-interval healing/shields not counted).',
            'experience':'Hero-panel XP deltas including one-level rollover; multi-level/gapped intervals flagged, never inferred from enemy types.',
             'items':'Confirmed ground pickup units require visible top-item plus inventory increase; returned DROP units excluded. Other inventory additions/keys/gold listed separately; identity changes are not pickups.',
             'journal_items':'Separate from backpack ground units: accepted guidebook pickup requires fresh matching public UI confirmation, actual arrival and ground disappearance. Older snapshots without UI have unknown journal coverage.',
            'coverage':'Missing observations, creation, simultaneous consumption/pickup, or identity changes can make item counts incomplete; deferral is never pickup.'}}


def from_rows(rows):
    metrics=FloorMetrics()
    losses=[];losses_available=False
    for row in rows:
        if 'accepted_transition' in row:
            t=row['accepted_transition'];metrics.accept(t['before'],t['action'],t['after'],row.get('index'),t.get('reason',''))
        if 'missed_loot' in row.get('result',{}):
            losses=list(row['result']['missed_loot']);losses_available=True
    report=metrics.report()
    report['missed_loot']=losses
    report['missed_loot_evidence_available']=losses_available
    for floor in report['floors']:
        floor['missed_loot']=[r for r in losses if (r['depth'],r.get('branch',0))==(floor['depth'],floor['branch'])]
        floor['missed_loot_incidents']=len(floor['missed_loot']) if losses_available else None
    report['definitions']['missed_loot']='Publicly confirmed unrecoverable rewards, not pickups or clear coverage; incident counts do not infer unknown item quantities. Older logs without the ledger have unknown coverage.'
    return report
