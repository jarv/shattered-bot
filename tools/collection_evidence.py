"""Narrow public-UI evidence for items collected outside the backpack."""


def journal_pickup(before,action,after):
    if action.get('type')!='cell' or before.get('depth')!=after.get('depth'):return None
    cell=action.get('cell')
    if after.get('hero',{}).get('cell')!=cell:return None
    obj=next((o for o in before.get('objects',[]) if o.get('cell')==cell
              and o.get('top_item') and not o.get('for_sale')),None)
    if not obj:return None
    title=obj['top_item']['name'].lower()
    # Guidebook.doPickUp unlocks journal pages instead of adding inventory.
    # Require the specific fresh public pickup confirmation, never name/absence alone.
    if title!='tome of dungeon mastery':return None
    message=f'you picked up: {title}.'
    texts=lambda state:{t.strip().lower() for t in state.get('ui',{}).get('texts',[])}
    if message not in texts(after)-texts(before):return None
    if any(o.get('cell')==cell and o.get('top_item',{}).get('name','').lower()==title
           for o in after.get('objects',[])):return None
    return title
