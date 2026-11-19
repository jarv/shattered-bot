"""Do not consume unidentified puzzle resources before clearing observed work."""
try:
    from .room_loot import room_region
    from .policy_geometry import neighbors,distance
    from .puzzle_supplies import demands
except ImportError:
    from room_loot import room_region
    from policy_geometry import neighbors,distance
    from puzzle_supplies import demands


def room_ready(p,state):
    if p.recent_threats or state.get('danger_cells'):return False
    region=room_region(p,state)
    if not region:return False
    width,height=state['map']['width'],state['map']['height']
    for cell in region:
        tile=p.tiles[cell]
        if not tile.get('visible') and not tile.get('observed'):return False
        if any(n not in p.tiles for n in neighbors(cell,width,height)):return False
    if any(c in region and not o.get('for_sale') for c,o in p.loot.items()):return False
    if any(c in region for c in p.room_actors):return False
    if p.mimic_obligations or p.potion_stash or p.trap_payload_return:return False
    if demands(p,state,distance):return False
    # A cleared *current room* does not rule out an undiscovered potion puzzle
    # elsewhere. Floor supplies are a conservation prior, never color identity.
    if getattr(p,'reserve_floor_puzzle_supplies',False):
        report=p.exploration_report(state,p.paths(state))
        unfinished={key:len(report[key]) for key in ('unvisited_reachable','unexplored_frontiers',
                    'unopened_doors','unresolved_doors','unreachable_known_floor','remaining_enemy_sightings')
                    if report[key]}
        if unfinished:
            p.planner.report['potion_reservation']={'reason':'Reserve unknown floor supplies while exploration is unfinished',
                'unfinished':unfinished,'identity_inferred':False}
            return False
    return True
