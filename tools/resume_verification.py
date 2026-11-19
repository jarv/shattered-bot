"""Verify a saved-run continuation from ordinary save-info/challenge windows."""
import re

try:
    from .policy_decision import Finished
except ImportError:
    from policy_decision import Finished


def verified_resume_policy(info,challenges,seed):
    try:
        from .nine_challenge import NineChallengePolicy,CHALLENGES
    except ImportError:
        from nine_challenge import NineChallengePolicy,CHALLENGES
    texts=[t.replace('_','').strip() for t in info.get('ui',{}).get('texts',[])]
    if info.get('scene')!='StartScene' or not info.get('modal') \
            or not any(re.fullmatch(r'level \d+ mage',t.lower()) for t in texts):
        raise Finished('blocked','Saved-run window does not visibly verify a Mage')
    if seed not in texts:raise Finished('blocked','Saved-run window does not visibly verify requested seed')
    checks=challenges.get('ui',{}).get('checkboxes',[])
    by_name={c['label'].strip().lower():c for c in checks}
    if challenges.get('scene')!='StartScene' or not challenges.get('modal') or len(checks)!=9 \
            or set(by_name)!=set(CHALLENGES) or not all(c.get('checked') is True for c in checks):
        raise Finished('blocked','Saved-run challenge panel must visibly show all nine checked challenges')
    policy=NineChallengePolicy(goal='survival',engine='legacy',seed=seed)
    policy.challenges_verified=policy.challenge_window_opened=True
    policy.verified_challenges=tuple(CHALLENGES)
    policy.verified_seed=seed
    return policy
