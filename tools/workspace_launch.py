"""Move only this launch's verified API process window; never the active window."""
import json
from pathlib import Path
import re
import subprocess


def clients():
    return json.loads(subprocess.run(['hyprctl','clients','-j'],check=True,capture_output=True,text=True).stdout)


def owned_window(windows,port,profile):
    found=[]
    for window in windows:
        if not window.get('mapped') or not isinstance(window.get('pid'),int):continue
        try:
            env=Path(f"/proc/{window['pid']}/environ").read_bytes().split(b'\0')
        except (OSError,ValueError):continue
        if f'SPD_API_PORT={port}'.encode() in env and f'SPD_DATA_DIR={profile}'.encode() in env:
            found.append(window)
    if len(found)!=1:raise RuntimeError(f'Expected one window owned by this API launch, found {len(found)}; refusing arbitrary window move')
    return found[0]


def move_command(address,workspace):
    if not re.fullmatch(r'0x[0-9a-fA-F]+',address) or not isinstance(workspace,int) or workspace<1:
        raise ValueError('Invalid exact window address/workspace')
    return ['hyprctl','dispatch',f'hl.dsp.window.move({{window = "address:{address}", workspace = {workspace}, follow = false}})']


def place(port,profile,workspace):
    window=owned_window(clients(),port,profile)
    if window['workspace']['id']!=workspace:
        moved=subprocess.run(move_command(window['address'],workspace),check=True,capture_output=True,text=True)
        if moved.stdout.strip()!='ok':raise RuntimeError('Hyprland did not confirm exact window placement: '+moved.stdout)
    after=next((w for w in clients() if w['address']==window['address']),None)
    if after is None or after['workspace']['id']!=workspace:raise RuntimeError('Requested game workspace was not verified')
    return {'address':after['address'],'pid':after['pid'],'workspace':workspace,'monitor':after['monitor']}
