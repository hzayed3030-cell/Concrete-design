# -*- coding: utf-8 -*-
import json, os, sys

def test_syntax():
    with open("modules/flat_slab.py", "r", encoding="utf-8") as f:
        code = f.read()
    import ast
    ast.parse(code)
    print("flat_slab.py is valid python!")

if __name__ == "__main__":
    test_syntax()
