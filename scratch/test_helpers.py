# -*- coding: utf-8 -*-
import json, os, io, math, re

def test_helpers():
    _CW_PRESETS_FILE = 'm1_manual_boq_presets.json'
    assert os.path.exists(_CW_PRESETS_FILE)
    with open(_CW_PRESETS_FILE, 'r', encoding='utf-8') as f:
        presets = json.load(f)
    print("Presets length:", len(presets))
    assert len(presets) == 12
    print("Test passed successfully!")

if __name__ == '__main__':
    test_helpers()
