import subprocess
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

with open('profiles.json', 'r', encoding='utf-8') as f:
    cur = json.load(f).get('profiles', {})

cmd = ['git', 'log', '--format=%H', '--', 'profiles.json']
commits = subprocess.check_output(cmd, encoding='utf-8').strip().split('\n')

for pname in cur:
    print(f"\n==================== PROFILE: {pname} ====================")
    found_any = False
    for c in reversed(commits):
        try:
            content = subprocess.check_output(['git', 'show', f'{c}:profiles.json'], encoding='utf-8')
            pdata = json.loads(content).get('profiles', {})
            if pname in pdata:
                d = pdata[pname].get('data', {})
                n_lx = d.get('fs_n_lx')
                n_ly = d.get('fs_n_ly')
                en = d.get('enabled_modules')
                rem = len(d.get('fs_removed_cols', [])) if isinstance(d.get('fs_removed_cols'), list) else 0
                trans = len(d.get('fs_col_transforms', {})) if isinstance(d.get('fs_col_transforms'), dict) else 0
                voids = len(d.get('fs_void_panels', [])) if isinstance(d.get('fs_void_panels'), list) else 0
                print(f"Commit {c[:8]}: en={en}, n_lx={n_lx}, n_ly={n_ly}, rem={rem}, trans={trans}, voids={voids}, keys={len(d)}")
                found_any = True
                break
        except Exception:
            pass
    
    # Also show current
    d = cur[pname].get('data', {})
    n_lx = d.get('fs_n_lx')
    n_ly = d.get('fs_n_ly')
    en = d.get('enabled_modules')
    rem = len(d.get('fs_removed_cols', [])) if isinstance(d.get('fs_removed_cols'), list) else 0
    trans = len(d.get('fs_col_transforms', {})) if isinstance(d.get('fs_col_transforms'), dict) else 0
    voids = len(d.get('fs_void_panels', [])) if isinstance(d.get('fs_void_panels'), list) else 0
    print(f"Current       : en={en}, n_lx={n_lx}, n_ly={n_ly}, rem={rem}, trans={trans}, voids={voids}, keys={len(d)}")
