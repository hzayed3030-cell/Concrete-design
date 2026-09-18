import subprocess
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

with open('profiles.json', 'r', encoding='utf-8') as f:
    cur = json.load(f).get('profiles', {})

cmd = ['git', 'log', '--format=%H', '--', 'profiles.json']
commits = subprocess.check_output(cmd, encoding='utf-8').strip().split('\n')

# Check each profile in cur against its fullest historical state
for pname, cur_p in cur.items():
    c_data = cur_p.get('data', {})
    best_commit = None
    best_keys_count = len(c_data)
    best_data = None
    
    for c in commits:
        try:
            content = subprocess.check_output(['git', 'show', f'{c}:profiles.json'], encoding='utf-8')
            pdata = json.loads(content).get('profiles', {})
            if pname in pdata:
                h_data = pdata[pname].get('data', {})
                if len(h_data) > best_keys_count:
                    best_keys_count = len(h_data)
                    best_commit = c
                    best_data = h_data
        except Exception:
            pass
            
    if best_commit:
        print(f"Profile: {pname}")
        print(f"  Current keys: {len(c_data)} | Best historical keys: {best_keys_count} (commit {best_commit[:8]})")
        # Check specific important fields
        h_nlx = best_data.get('fs_n_lx')
        c_nlx = c_data.get('fs_n_lx')
        h_rem = len(best_data.get('fs_removed_cols', []))
        c_rem = len(c_data.get('fs_removed_cols', []))
        h_trans = len(best_data.get('fs_col_transforms', {}))
        c_trans = len(c_data.get('fs_col_transforms', {}))
        print(f"  Grid: current={c_nlx}x{c_data.get('fs_n_ly')} vs hist={h_nlx}x{best_data.get('fs_n_ly')}")
        print(f"  Removed cols: current={c_rem} vs hist={h_rem}")
        print(f"  Col transforms: current={c_trans} vs hist={h_trans}")
