
def get_symbol_layout(cell_x, cell_y, cell_w, cell_h, count):
    """
    Returns symbol center positions and icon size for 1-4 events in a day cell.

    Logic:
      1 event  -> one large centered symbol
      2 events -> left / right
      3 events -> triangle: two top, one bottom
      4 events -> 2x2 grid

    For 2, 3 and 4 events, all symbols use the same size.
    """
    if count < 1:
        return [], 0

    cx = cell_x + cell_w / 2
    cy = cell_y + cell_h / 2

    # One single event gets a larger icon.
    if count == 1:
        icon_size = int(min(cell_w, cell_h) * 0.42)
        return [(cx, cy)], icon_size

    # 2-4 events all use the same icon size.
    icon_size = int(min(cell_w, cell_h) * 0.27)

    dx = cell_w * 0.23
    dy = cell_h * 0.20

    if count == 2:
        positions = [
            (cx - dx, cy),
            (cx + dx, cy),
        ]

    elif count == 3:
        positions = [
            (cx - dx, cy - dy),
            (cx + dx, cy - dy),
            (cx,      cy + dy),
        ]

    else:
        positions = [
            (cx - dx, cy - dy),
            (cx + dx, cy - dy),
            (cx - dx, cy + dy),
            (cx + dx, cy + dy),
        ]

    return positions, icon_size


def draw_day_symbols(draw, events, cell_x, cell_y, cell_w, cell_h, draw_symbol):
    """
    Draw up to 4 event symbols inside one calendar day cell.

    `events` may contain any event objects/dicts your calendar already uses.
    `draw_symbol(event, center_x, center_y, size)` is your existing/icon-specific
    rendering callback.
    """
    visible_events = events[:4]
    positions, icon_size = get_symbol_layout(
        cell_x, cell_y, cell_w, cell_h, len(visible_events)
    )

    for event, (cx, cy) in zip(visible_events, positions):
        draw_symbol(event, cx, cy, icon_size)
