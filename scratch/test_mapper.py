def create_axis_mapper(old_coords, new_coords, old_cant_min=0.0, new_cant_min=0.0, old_cant_max=0.0, new_cant_max=0.0):
    """
    Creates a mapping function from old 1D coordinate to new 1D coordinate.
    Matches axes exactly if within a snapping tolerance, interpolates proportionally
    within spans, and handles cantilevers properly.
    """
    n_old = len(old_coords)
    n_new = len(new_coords)

    def map_coord(val):
        # 1. Exact or near axis snap (within 0.35m of an old axis)
        best_i = None
        best_d = 0.35
        for i, oc in enumerate(old_coords):
            d = abs(val - oc)
            if d < best_d:
                best_d = d
                best_i = i

        if best_i is not None:
            # If same number of axes or valid index in new_coords
            if best_i < n_new:
                offset_from_axis = val - old_coords[best_i]
                return round(new_coords[best_i] + offset_from_axis, 4)

        # 2. Cantilever left/bottom (val < old_coords[0])
        if val < old_coords[0]:
            dist_out = old_coords[0] - val
            if old_cant_min > 0.01 and new_cant_min > 0.01:
                ratio = new_cant_min / old_cant_min
                return round(new_coords[0] - (dist_out * ratio), 4)
            else:
                return round(new_coords[0] - dist_out, 4)

        # 3. Cantilever right/top (val > old_coords[-1])
        if val > old_coords[-1]:
            dist_out = val - old_coords[-1]
            if old_cant_max > 0.01 and new_cant_max > 0.01:
                ratio = new_cant_max / old_cant_max
                return round(new_coords[-1] + (dist_out * ratio), 4)
            else:
                return round(new_coords[-1] + dist_out, 4)

        # 4. In-between spans interpolation
        for k in range(n_old - 1):
            x_a = old_coords[k]
            x_b = old_coords[k + 1]
            if x_a <= val <= x_b:
                span_len_old = x_b - x_a
                ratio = (val - x_a) / span_len_old if span_len_old > 1e-6 else 0.0
                if k < n_new - 1:
                    nx_a = new_coords[k]
                    nx_b = new_coords[k + 1]
                    return round(nx_a + ratio * (nx_b - nx_a), 4)
                elif n_new > 0:
                    return round(new_coords[-1], 4)

        return round(val, 4)

    return map_coord

# Quick test
old_x = [0.0, 5.0, 10.0, 15.0]
new_x = [0.0, 6.0, 11.0, 16.0]
mapper = create_axis_mapper(old_x, new_x)
print("x=0.0 ->", mapper(0.0))
print("x=5.0 ->", mapper(5.0))
print("x=10.0 ->", mapper(10.0))
print("x=15.0 ->", mapper(15.0))
print("x=2.5 (mid) ->", mapper(2.5))
print("x=-1.5 (cant) ->", mapper(-1.5))
