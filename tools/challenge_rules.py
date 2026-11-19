"""Explicit immutable rule configuration; a regular game is the default.

The same selection controls ordinary startup checkboxes and rule admission.
Never infer challenge settings from hidden game state or enable a bundle just
because another challenge is selected.
"""
from dataclasses import dataclass,fields,replace

CHALLENGES=(
    'hostile champions','badder bosses','on diet','faith is my armor',
    'pharmacophobia','barren land','swarm intelligence','into darkness','forbidden runes',
)
CHALLENGE_OPTIONS=tuple(name.replace(' ','-') for name in CHALLENGES)
PRESETS=('regular','all-nine','eight-without-on-diet')


@dataclass(frozen=True)
class ChallengeRules:
    hostile_champions: bool=False
    badder_bosses: bool=False
    on_diet: bool=False
    faith_is_my_armor: bool=False
    pharmacophobia: bool=False
    barren_land: bool=False
    swarm_intelligence: bool=False
    into_darkness: bool=False
    forbidden_runes: bool=False

    def __post_init__(self):
        for f in fields(self):
            if not isinstance(getattr(self,f.name),bool):
                raise ValueError(f'{f.name} must be an explicit boolean')

    @property
    def enabled_challenges(self):
        return tuple(name for name in CHALLENGES if getattr(self,name.replace(' ','_')))

    @property
    def combat_pressure(self):
        return self.hostile_champions or self.swarm_intelligence

    @property
    def scarce_recovery(self):
        return self.pharmacophobia or self.on_diet

    @property
    def mode(self):
        enabled=self.enabled_challenges
        if not enabled:return 'regular'
        if len(enabled)==9:return 'all-nine'
        if enabled==tuple(n for n in CHALLENGES if n!='on diet'):return 'eight-without-on-diet'
        return 'custom'

    def as_dict(self):
        return {f.name:getattr(self,f.name) for f in fields(self)}

    def with_option(self,name,enabled):
        field=name.replace('-','_').replace(' ','_')
        if field not in self.as_dict():raise ValueError(f'Unknown challenge: {name}')
        return replace(self,**{field:enabled})

    @classmethod
    def preset(cls,name):
        if name not in PRESETS:raise ValueError(f'Unknown challenge preset: {name}')
        if name=='regular':return cls()
        return cls(**{f.name:name=='all-nine' or f.name!='on_diet' for f in fields(cls)})


def configured_rules(preset='regular',enable=(),disable=()):
    if set(enable)&set(disable):raise ValueError('Cannot enable and disable the same challenge')
    rules=ChallengeRules.preset(preset)
    for option in enable:rules=rules.with_option(option,True)
    for option in disable:rules=rules.with_option(option,False)
    return rules
