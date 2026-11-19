"""Set/reopen/verify a user-selected seed through the ordinary seed dialog."""
import re


def normalize(seed):
    if seed is None:
        return None
    letters=seed.replace("-","").strip().upper()
    if not re.fullmatch(r"[A-Z]{9}",letters):
        raise ValueError("Use a nine-letter seed code such as ABC-DEF-GHI")
    return "-".join(letters[i:i+3] for i in range(0,9,3))


def seed_menu(p,state):
    if p.requested_seed is None or p.verified_seed is not None:
        return None
    p.seed_steps += 1
    if p.seed_steps>14:
        p.stop_unsafe("Seed startup exceeded its UI verification budget")
    ui=state["ui"]
    buttons=ui["buttons"]
    if "text_input" in ui:
        title=" ".join(ui.get("texts",[])).lower()
        if "enter a custom seed" not in title:
            p.stop_unsafe("Unexpected text dialog during seed verification")
        if ui["text_input"] != p.requested_seed:
            if p.seed_submitted:
                p.stop_unsafe("Reopened seed dialog does not match the requested seed")
            return p.decision({"type":"text","text":p.requested_seed},"seed: type requested code into visible field")
        if p.seed_submitted:
            button=next((b for b in buttons if b["label"].strip().lower()=="set"),None)
            if not button:
                p.stop_unsafe("Verified seed dialog has no ordinary Set control")
            p.verified_seed=p.requested_seed
            return p.decision({"type":"button","id":button["id"]},"seed: verify saved code by reopening and confirming the ordinary dialog")
        button=next((b for b in buttons if b["label"].strip().lower()=="set"),None)
        if button:
            p.seed_submitted=True
            return p.decision({"type":"button","id":button["id"]},"seed: submit visible custom seed")
    button=next((b for b in buttons if b["label"].strip().lower()=="custom seed"),None)
    if button:
        return p.decision({"type":"button","id":button["id"]},"seed: reopen for verification" if p.seed_submitted else "seed: open ordinary custom-seed dialog")
    options=next((b for b in buttons if b["label"].strip().lower()=="game options"),None)
    if options and not p.seed_options_opened:
        p.seed_options_opened=True
        return p.decision({"type":"button","id":options["id"]},"seed: open ordinary game options")
    p.stop_unsafe("Custom seed UI unavailable; refusing unverified random game")
