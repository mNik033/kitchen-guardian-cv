import math

def calculate_center(box: list) -> tuple:
    """
    Calculate the center point of a bounding box [x1, y1, x2, y2].
    """
    x1, y1, x2, y2 = box
    center_x = int((x1 + x2) / 2)
    center_y = int((y1 + y2) / 2)
    return (center_x, center_y)

def is_point_in_zones(point: tuple, zones: list, radius: int) -> bool:
    """
    Check if a given point is within 'radius' distance of any point in 'zones'.
    """
    px, py = point
    for zx, zy in zones:
        distance = math.sqrt((px - zx)**2 + (py - zy)**2)
        if distance <= radius:
            return True
    return False
