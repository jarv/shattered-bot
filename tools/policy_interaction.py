"""Validated UI state machines. Unknown menus fail closed, never guess."""
from enum import Enum
import re

try:
    from .policy_decision import Finished
    from .shop_tactics import confirm_purchase
    from .consumable_tactics import discovery_menu
    from .resource_tactics import enchantment_menu
    from .combat_items import stats, physical_score
except ImportError:
    from policy_decision import Finished
    from shop_tactics import confirm_purchase
    from consumable_tactics import discovery_menu
    from resource_tactics import enchantment_menu
    from combat_items import stats, physical_score


class MenuPhase(str, Enum):
    UPGRADE_CANCEL = "upgrade-cancel"
    DISCOVER_SCROLL = "discover-scroll"
    ENCHANT_SELECT = "enchant-select"
    ENCHANT_CHOICE = "enchant-choice"
    UPGRADE_SELECT = "upgrade-select"
    UPGRADE_HOLSTER_SELECT = "upgrade-holster-select"
    UPGRADE_CONFIRM = "upgrade-confirm"
    IDENTIFY_SELECT = "identify-select"


def cancel_upgrade(p, state):
    p.menu_plan = None
    return p.decision({"type": "back"}, "upgrade: retain unspent scroll for allocation")


def select_upgrade(p, state):
    buttons = state["ui"]["buttons"]
    button = next((b for b in buttons if b["label"].lower() == (p.upgrade_target or "").lower()), None) \
        if p.upgrade_target else next((b for b in buttons if "staff of magic missile" in b["label"].lower()), None)
    if button:
        p.menu_plan = MenuPhase.UPGRADE_CONFIRM
        return p.decision({"type": "button", "id": button["id"]}, "upgrade: select staff")
    # Upgrade opens the backpack, but carried spare wands can be in a holster.
    # Navigate only the observed tab for the already allocated carried wand.
    # A separate phase bounds this to one attempt; absence afterward fails closed.
    target = next((i for i in state.get("inventory", [])
                   if i["name"].lower() == (p.upgrade_target or "").lower()
                   and i["name"].lower().startswith("wand of ")
                   and i.get("upgradable") and "ZAP" in i.get("actions", [])), None)
    holster = next((b for b in buttons if b["label"].lower() == "magical holster"), None)
    if p.menu_plan == MenuPhase.UPGRADE_SELECT and target and holster:
        p.menu_plan = MenuPhase.UPGRADE_HOLSTER_SELECT
        return p.decision({"type": "button", "id": holster["id"]},
                          "upgrade: open holster for allocated wand")


def confirm_upgrade(p, state):
    button = next((b for b in state["ui"]["buttons"] if b["label"].lower() == "upgrade"), None)
    if button:
        p.menu_plan = None
        p.upgrade_target = None
        return p.decision({"type": "button", "id": button["id"]}, "upgrade: confirm")


def select_identify(p, state):
    button = next((b for b in state["ui"]["buttons"] if "potion" in b["label"].lower()), None)
    if button:
        p.menu_plan = None
        return p.decision({"type": "button", "id": button["id"]}, "identify: potion")


MENU_HANDLERS = {
    MenuPhase.UPGRADE_CANCEL: cancel_upgrade,
    MenuPhase.DISCOVER_SCROLL: discovery_menu,
    MenuPhase.ENCHANT_SELECT: enchantment_menu,
    MenuPhase.ENCHANT_CHOICE: enchantment_menu,
    MenuPhase.UPGRADE_SELECT: select_upgrade,
    MenuPhase.UPGRADE_HOLSTER_SELECT: select_upgrade,
    MenuPhase.UPGRADE_CONFIRM: confirm_upgrade,
    MenuPhase.IDENTIFY_SELECT: select_identify,
}


def confirm_enhanced_throw(p, state):
    """Continue only the selected combat throw, not arbitrary Yes/No dialogs.

    The warning precedes targeting and spends neither a turn nor the weapon.
    Accepting permits the already chosen last use (including its stated loss);
    it is not a hit, breakage, or collection receipt.
    """
    warning = ("If the last thrown weapon in your enhanced thrown weapon set breaks, "
               "the set will be permanently lost. Are you sure you want to throw it?")
    texts = state["ui"].get("texts", [])
    buttons = state["ui"]["buttons"]
    last = getattr(p, "last_decision", None)
    action = last.action if last else {}
    if warning not in texts or len(buttons) != 2 \
            or {b["label"] for b in buttons} != {"Yes", "No"} \
            or action.get("type") != "item" or action.get("action") != "THROW" \
            or p.target is None:
        return None
    item = next((i for i in state.get("inventory", [])
                 if i.get("id") == action.get("id")), None)
    enemy = next((o for o in state.get("objects", [])
                  if o.get("cell") == p.target and o.get("health_bar")
                  and not o.get("top_item")), None)
    value = stats(item) if item else None
    if not item or not enemy or not value or value[0] != "thrown" \
            or not texts or texts[0].lower() != item["name"].lower() \
            or "THROW" not in item.get("actions", []) \
            or physical_score(item, state["hero"].get("strength", 0)) <= 0 \
            or not p.item_action_allowed(item, "THROW") \
            or not p.target_allowed(item, enemy) \
            or not p.attack_kind_allowed(state, enemy, "thrown") \
            or not p.shot_clear(state, p.target):
        return None
    yes = next(b for b in buttons if b["label"] == "Yes")
    return p.decision({"type": "button", "id": yes["id"]},
                      "combat: confirm selected enhanced throw with last-use loss warning")


def menu(p, state):
    buttons = state["ui"]["buttons"]
    if state["scene"] != "GameScene":
        preferred = {
            "WelcomeScene": ("enter the dungeon",),
            "TitleScene": ("play",),
            "StartScene": ("new game",),
            "HeroSelectScene": ("start", "mage"),
        }.get(state["scene"], ())
        if state["scene"] == "HeroSelectScene" and not any("mage" == t.lower() for t in state["ui"]["texts"]):
            preferred = ("mage",)
        for label in preferred:
            button = next((b for b in buttons if b["label"].lower() == label), None)
            if button:
                return p.decision({"type": "button", "id": button["id"]}, f"menu: {label}")
        raise Finished("blocked", f"Unsupported startup menu: {state['scene']} {state['ui']}")
    if p.shop_plan:
        return confirm_purchase(p, state)
    if any(re.fullmatch(r"buy for \d+g", b["label"].strip().lower()) for b in buttons):
        return p.decision({"type": "back"}, "shop: dismiss unplanned stock window")
    if any(t.strip().lower() == "a message from the developer" for t in state["ui"].get("texts", [])):
        close = next((b for b in buttons if b["label"].strip().lower() == "close"), None)
        if close:
            return p.decision({"type": "button", "id": close["id"]}, "menu: close developer information")
    journal_tabs = {"adventuring notes", "dungeon guide", "alchemy guide", "catalogs", "badges"}
    labels = {b["label"].strip().lower() for b in buttons}
    if len(journal_tabs & labels) >= 3 and {"this run", "overall"}.issubset(labels):
        return p.decision({"type": "back"}, "menu: dismiss journal badges information")
    if p.menu_plan is None and any("upgrading an item permanently improves it" in t.lower()
                                   for t in state["ui"].get("texts", [])):
        p.menu_plan = MenuPhase.UPGRADE_CANCEL
        return p.decision({"type": "back"}, "upgrade: leave automatic next-upgrade preview")
    if p.menu_plan:
        phase = p.menu_plan
        result = MENU_HANDLERS[phase](p, state)
        if result is not None:
            return result
        raise Finished("blocked", f"Cannot complete {phase.value}: {state['ui']}")
    throw = confirm_enhanced_throw(p, state)
    if throw:
        return throw
    if labels == {"settings", "challenges", "main menu"}:
        return p.decision({"type": "back"}, "menu: close ordinary in-game pause menu without changing settings")
    if not buttons:
        return p.decision({"type": "back"}, "menu: dismiss information")
    raise Finished("blocked", f"Unhandled game menu: {state['ui']}")
