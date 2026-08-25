# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all, copy_metadata

block_cipher = None

datas = [
    ('app.py', '.'),
    ('modules', 'modules'),
]
binaries = []
hiddenimports = [
    'streamlit',
    'streamlit.web.cli',
    'streamlit.runtime.scriptrunner.magic_expressions',
    'pandas',
    'matplotlib',
    'matplotlib.backends.backend_agg',
    'modules.columns',
    'modules.footings',
    'modules.flat_slab',
    'modules.steel_bars',
    'modules.concrete_survey',
    'modules.plan_boundary',
    'modules.report_generator',
    'modules.settings',
]

# Collect metadata and files for Streamlit and other critical packages
datas += copy_metadata('streamlit')
for pkg in ['streamlit', 'altair', 'pydeck', 'watchdog', 'tornado', 'pandas', 'matplotlib']:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Warning collecting {pkg}: {e}")

a = Analysis(
    ['run_app.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ECP203_Dashboard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
