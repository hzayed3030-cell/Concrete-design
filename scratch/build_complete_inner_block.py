# -*- coding: utf-8 -*-
"""
Script to write the complete inner BOQ replacement block to scratch/inner_code_template.py
"""
import ast

def main():
    with open("scratch/create_inner_template.py", "w", encoding="utf-8") as f:
        f.write("# inner template creator\n")

if __name__ == "__main__":
    main()
