"""
Module 13 -- Standalone Flat Slabs Design (ECP 203)
تصميم بلاطات فلات سلاب مستقلة (Direct Design Method & Detailing)
100% Standalone - No dependencies on Columns, Footings, or Ground Beams.
"""

from modules.flat_slab import render as _render_flat_slab


def render():
    """
    Render Module 13: Standalone Flat Slabs.
    Calls flat_slab.render with is_standalone=True, omitting:
      - Column Reactions & Vertical Loads
      - Column Reactions Table
      - Governing Column Loads by Type
      - Exporting column loads to Module 2 & 7
      - Rectangular Columns Design
      - Building Foundations Design
      - Ground Beams Design
      - Foundation Layout Sketch
      - Approximate Quantity Survey
    While keeping 100% of Flat Slab design steps, verification, punching shear,
    bending moments, extra rebar, deflection optimization, and all 10 engineering sketches.
    """
    _render_flat_slab(is_standalone=True)
