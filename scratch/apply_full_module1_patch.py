# -*- coding: utf-8 -*-
"""
Complete patch application script for modules/flat_slab.py.
"""
import ast, os, re, py_compile

def main():
    print("Reading modules/flat_slab.py...")
    with open("modules/flat_slab.py", "r", encoding="utf-8") as f:
        src = f.read()

    # 1. Get top helpers
    import sys
    sys.path.insert(0, "scratch")
    from build_complete_m1_patch import get_helpers_block
    top_helpers = get_helpers_block()

    # 2. Get inner replacement code
    with open("scratch/inner_code_template.py", "r", encoding="utf-8") as f:
        inner_code = f.read()

    # Verify positions
    render_idx = src.find("def render(is_standalone: bool = False):")
    if render_idx == -1:
        raise ValueError("Could not find 'def render' in modules/flat_slab.py")

    p_start = src.find("# ── جسر المزامنة الفورية لتوصيفات البنود (Hidden Sync Bridge) ──")
    p_end = src.find("# ── 💾 SAVE & EXPORT COMPLETE CALCULATION SHEET (COLLAPSED EXPANDER) ────────")

    if p_start == -1 or p_end == -1:
        raise ValueError(f"Could not find block boundaries: p_start={p_start}, p_end={p_end}")

    print(f"Found boundaries: render_idx={render_idx}, p_start={p_start}, p_end={p_end}")

    # Replace expander title
    old_title = '🏗️ حصر شامل لجميع الأعمال الخاصة بالمبنى'
    new_title = 'جداول الحصر والتكلفة لجميع البنود'
    if old_title not in src[:p_start]:
        print("Warning: old title not found before p_start")
    else:
        src = src.replace(old_title, new_title, 1)
        # Recalculate positions after title replacement
        render_idx = src.find("def render(is_standalone: bool = False):")
        p_start = src.find("# ── جسر المزامنة الفورية لتوصيفات البنود (Hidden Sync Bridge) ──")
        p_end = src.find("# ── 💾 SAVE & EXPORT COMPLETE CALCULATION SHEET (COLLAPSED EXPANDER) ────────")

    # Step A: Replace inner block
    patched_inner = src[:p_start] + inner_code + "\n        " + src[p_end:]

    # Step B: Insert top helpers before render()
    render_idx = patched_inner.find("def render(is_standalone: bool = False):")
    final_src = patched_inner[:render_idx] + "\n" + top_helpers + "\n\n" + patched_inner[render_idx:]

    print("Verifying final AST of complete patched file...")
    ast.parse(final_src)
    print("AST parse successful!")

    # Write to a test file first
    test_out = "scratch/flat_slab_patched_final.py"
    with open(test_out, "w", encoding="utf-8") as f:
        f.write(final_src)

    print(f"Compiling {test_out} with py_compile...")
    py_compile.compile(test_out, doraise=True)
    print("py_compile successful!")

    # Backup original flat_slab.py if not already backed up
    backup_file = "modules/flat_slab.py.bak_boq"
    if not os.path.exists(backup_file):
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"Created backup at {backup_file}")

    # Overwrite modules/flat_slab.py
    with open("modules/flat_slab.py", "w", encoding="utf-8") as f:
        f.write(final_src)
    print("Successfully patched modules/flat_slab.py!")

    # Verify modules/flat_slab.py
    py_compile.compile("modules/flat_slab.py", doraise=True)
    print("Verified modules/flat_slab.py py_compile OK!")

if __name__ == "__main__":
    main()
