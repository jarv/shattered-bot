"""Public-species capabilities and configurable strategy groups, not live stats."""
from dataclasses import dataclass,replace,asdict
from types import MappingProxyType


@dataclass(frozen=True)
class UnitProfile:
    name: str
    strategy: str='melee'
    movement: str='ground'
    urgency: int=10
    capabilities: tuple=()
    protected: bool=False

    @property
    def triggers_ground_plants(self):
        return self.movement=='ground'


OVERRIDE_STRATEGIES=frozenset({'melee','ranged-first','ranged','flying-melee','thief','stationary'})


def defaults():
    # Import at construction, after the primitive policy module has loaded.
    try:
        from .survival_policy import ENEMIES
    except ImportError:
        from survival_policy import ENEMIES
    profiles={name:UnitProfile(name) for name in ENEMIES}
    def group(names,strategy,movement='ground',urgency=10,capabilities=(),protected=False):
        for name in names:
            profiles[name]=UnitProfile(name,strategy,movement,urgency,capabilities,protected)
    group(('sewer crab','hermit crab','dwarf monk','senior monk','ripper demon'),
          'ranged-first',urgency=45,capabilities=('fast-melee',))
    group(('vampire bat','golden bee'),'flying-melee','flying',25,('flight',))
    for name in ('sewer crab','vampire bat'):
        profiles[name]=replace(profiles[name],capabilities=(*profiles[name].capabilities,'fast-movement'))
    group(('swarm of flies',),'fly-swarm','flying',65,('flight','physical-hit-splitting'),True)
    group(('sewer snake',),'evasive',urgency=50,capabilities=('evasive','surprise-vulnerable'),protected=True)
    group(('wraith','tormented spirit'),'wraith','flying',55,('flight','physical-evasion'),True)
    group(('skeleton','dwarven skeleton'),'undead',urgency=50,capabilities=('death-blast',),protected=True)
    group(('necromancer','spectral necromancer',"necromancer's skeleton"),
          'summoner',urgency=75,capabilities=('linked-summons',),protected=True)
    group(('crazy thief','crazy bandit'),'thief',urgency=55,capabilities=('theft','fleeing'))
    group(('dm-100','modified dm-100','gnoll shaman','dwarf warlock','scorpio','acidic scorpio','captured shaman',
           'fungal sentry','gnoll geomancer','gnoll sapper'),
          'ranged',urgency=60,capabilities=('ranged-attacks',))
    group(('evil eye',),'ranged','flying',65,('flight','ranged-attacks','advertised-charge'))
    group(('crystal wisp',),'ranged','flying',60,('flight','ranged-attacks'))
    group(('prison guard',),'ranged',urgency=60,capabilities=('ranged-pull',))
    group(('fire elemental','newborn fire elemental','frost elemental','shock elemental','chaos elemental','greater elemental'),
          'flying-melee','flying',30,('flight','elemental'))
    group(('demon spawner','dm-201','crystal spire','fungal core'),'stationary','stationary',40,('stationary',))
    group(('mimic','golden mimic','ebony mimic'),'mimic',urgency=35,capabilities=('chest-ambush',),protected=True)
    group(('crystal mimic',),'crystal-mimic',urgency=85,capabilities=('theft','fleeing','displacement'),protected=True)
    group(('giant piranha','phantom piranha'),'aquatic','aquatic',50,('water-bound',),True)
    for name in ('fetid rat','gnoll trickster','great crab'):
        capabilities=('ghost-quest','ranged-attacks','fleeing','poison-darts') if name=='gnoll trickster' else ('ghost-quest',)
        group((name,),'quest:'+name,urgency=90,capabilities=capabilities,protected=True)
    for name in ('goo','tengu','dm-300','king of dwarves','yog-dzewa'):
        group((name,),'boss:'+name,'stationary' if name=='yog-dzewa' else 'ground',100,('boss',),True)
    for name in ('burning fist','soiled fist','rotting fist','rusted fist','bright fist','dark fist'):
        group((name,),'boss:yog-dzewa','ground',100,('boss-add',),True)
    return profiles


class StrategyBook:
    """Immutable profile book; per-engagement state belongs to policy memory."""
    def __init__(self,overrides=None):
        profiles=defaults()
        if overrides is not None and not isinstance(overrides,dict):raise ValueError('Unit strategies must be a JSON object')
        for name,strategy in (overrides or {}).items():
            if name not in profiles:raise ValueError(f'Unknown public enemy name: {name}')
            if not isinstance(strategy,str) or strategy not in OVERRIDE_STRATEGIES:raise ValueError(f'Unsupported ordinary unit strategy: {strategy}')
            if profiles[name].protected:raise ValueError(f'{name} requires its dedicated strategy')
            profiles[name]=replace(profiles[name],strategy=strategy)
        self._profiles=MappingProxyType(profiles)
        self.overrides=MappingProxyType(dict(overrides or {}))

    def __deepcopy__(self,memo):
        return self  # Only frozen profiles and read-only mappings are shared.

    def profile(self,enemy):
        name=enemy['name'].lower()
        return self._profiles.get(name,UnitProfile(name,'unknown','unknown',0,('unclassified',)))

    def describe(self,enemy):
        result=asdict(self.profile(enemy));result['cell']=enemy['cell']
        result['triggers_ground_plants']=self.profile(enemy).triggers_ground_plants
        result['evidence']='Public species profile, not hidden HP, identity, timer or live movement buff'
        return result

    def allows_funnel(self,enemies):
        return all(self.profile(e).strategy in {'melee','flying-melee','fly-swarm','undead','mimic','evasive'}
                   for e in enemies if not e.get('sleeping'))
