"""Conservative geometry using only the observed grid."""
BEAM_BLOCKERS = {0, 4, 5, 10, 12, 13, 16, 21, 23, 25, 26, 27, 28, 31, 33, 34, 35, 36, 38, 39}


def navigation_terrain(terrain):
    """Semantic progress only; NEVER use this normalization for movement or shots."""
    return 5 if terrain in {5,6} else terrain


def distance(a, b, width):
    return max(abs(a % width - b % width), abs(a // width - b // width))


def neighbors(cell, width, height):
    x, y = cell % width, cell // width
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if (dx or dy) and 0 <= x + dx < width and 0 <= y + dy < height:
                yield (y + dy) * width + x + dx


def line_clear(source, target, width, tiles):
    """Conservative Bresenham visibility; no engine/internal collision queries."""
    x, y, tx, ty = source % width, source // width, target % width, target // width
    dx, dy = abs(tx - x), -abs(ty - y)
    sx, sy = (1 if x < tx else -1), (1 if y < ty else -1)
    error = dx + dy
    while (x, y) != (tx, ty):
        twice = 2 * error
        if twice >= dy:
            error += dy
            x += sx
        if twice <= dx:
            error += dx
            y += sy
        cell = y * width + x
        if cell == target:
            return True
        if cell not in tiles or tiles[cell]["terrain"] in BEAM_BLOCKERS:
            return False
    return True


def projectile_line_clear(source,target,width,tiles):
    """Public major-axis projectile rule, using observed terrain only.

    Integer half-error/tie rounding differs from the older generic Bresenham.
    No engine collision queries, hidden actors or unobserved terrain are read.
    """
    if source==target:return True
    dx,dy=abs(target%width-source%width),abs(target//width-source//width)
    sx=1 if target%width>source%width else -1
    sy=1 if target//width>source//width else -1
    major,minor,a,b=(dx,dy,sx,sy*width) if dx>dy else (dy,dx,sy*width,sx)
    error=major//2;cell=source
    for _ in range(major):
        cell+=a;error+=minor
        if error>=major:cell+=b;error-=major
        if cell==target:return True
        # A chasm stops walking, not a bolt. Treating pits as cover caused the
        # floor-11 shaman death and also hid legal return shots from the Mage.
        if cell not in tiles or tiles[cell]['terrain'] in BEAM_BLOCKERS-{0}:return False
    return False
