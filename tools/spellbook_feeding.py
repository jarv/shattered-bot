"""Feed only identified scrolls explicitly named by the public current index."""
try:
    from .consumable_tactics import base_name
    from .combat_items import known_cursed
    from .artifact_tactics import artifact_name
    from .inventory_tactics import quiet
except ImportError:
    from consumable_tactics import base_name
    from combat_items import known_cursed
    from artifact_tactics import artifact_name
    from inventory_tactics import quiet


MARKER='its index is currently pointing to the following blank pages:'
RESERVE={'scroll of identify','scroll of remove curse','scroll of teleportation','scroll of recharging',
         'scroll of mirror image','scroll of terror'}


def requests(book):
    text=book.get('description','').replace('_','').lower()
    if MARKER not in text:return set()
    block=text.split(MARKER,1)[1].strip().split('\n\n',1)[0]
    return {line.strip() for line in block.splitlines() if line.strip().startswith('scroll of ')}


def count(state,name):
    return sum(i.get('quantity',1) for i in state['inventory'] if base_name(i)==name)


def candidates(state,book):
    wanted=requests(book)
    return [i for i in state['inventory'] if i.get('identified') and base_name(i) in wanted
            and base_name(i) not in {'scroll of upgrade','scroll of transmutation'}
            and (base_name(i) not in RESERVE or count(state,base_name(i))>1)
            and not (base_name(i)=='scroll of remove curse'
                     and any(known_cursed(j) for j in state['inventory']))]


def choose(p,state,enemies,book):
    if not book or 'ADD' not in book.get('actions',[]) or not book.get('curse_known') or known_cursed(book) \
            or not quiet(p,state,enemies) or state['hero']['hp']<.8*state['hero']['max_hp']:return None
    choices=candidates(state,book)
    for item in choices:
        key=('book-add',book['name'],tuple(sorted(requests(book))),base_name(item))
        if p.artifact_extension_attempts[key]:continue
        p.artifact_extension_attempts[key]+=1
        p.artifact_menu={'kind':'spellbook-add','stage':'select','steps':0,'bags':[],
                         'name':base_name(item),'label':item['name'].lower(),'before':count(state,base_name(item)),
                         'book_before':book['name'],'index_before':sorted(requests(book))}
        return p.use(book,'ADD','artifact: add identified scroll explicitly requested by current Spellbook index')
    return None


def observe(p,state):
    plan=p.artifact_menu
    if not isinstance(plan,dict) or plan.get('kind')!='spellbook-add' or plan.get('stage')!='verify' \
            or state.get('status')!='ready' or state.get('modal'):return
    book=next((i for i in state['inventory'] if artifact_name(i)=='unstable spellbook' and i.get('equipped')),None)
    consumed=plan['before']-count(state,plan['name'])==1
    changed=bool(book and (book['name']!=plan['book_before'] or sorted(requests(book))!=plan['index_before']))
    p.planner.report['spellbook_add']={'name':plan['name'],'scroll_consumption_observed':consumed,
        'book_change_observed':changed,'confirmed':consumed and changed,
        'qualification':'Requires one scroll consumed and public book level/index change; no arbitrary-scroll feed or retry'}
    if not (consumed and changed):
        p.log_continuation_error(state,'spellbook-add-unconfirmed','No confirmed requested-scroll addition; do not repeat',dict(plan))
    p.artifact_menu=None


def menu(p,state,plan):
    plan['steps']+=1
    if plan['steps']>8:
        p.stop_unsafe('Spellbook ADD exceeded bounded public selector workflow')
    if plan['stage']=='verify':
        return p.decision({'type':'back'},'artifact: close Spellbook ADD selector before verifying result')
    book=next((i for i in state['inventory'] if artifact_name(i)=='unstable spellbook' and i.get('equipped')),None)
    valid=book and any(base_name(i)==plan['name'] and i['name'].lower()==plan['label'] for i in candidates(state,book))
    buttons=[b for b in state['ui'].get('buttons',[]) if b.get('enabled',True)]
    label=lambda b:b['label'].replace('_','').strip().lower()
    text=' '.join(state['ui'].get('texts',[])).lower()
    if valid and 'select a scroll' in text:
        target=[b for b in buttons if label(b)==plan['label']]
        if len(target)==1:
            plan['stage']='verify'
            return p.decision({'type':'button','id':target[0]['id']},'artifact: feed only the identified scroll named in current blank pages')
        bag=next((b for b in buttons if label(b) in {'scroll holder','magical holster','backpack'}
                  and label(b) not in plan['bags']),None)
        if bag:
            plan['bags'].append(label(bag))
            return p.decision({'type':'button','id':bag['id']},'artifact: locate requested identified scroll in observed bag')
    p.artifact_menu=None
    return p.decision({'type':'back'},'artifact: cancel changed or unsupported Spellbook ADD request')
