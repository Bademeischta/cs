import numpy as np

class MathEngine:
    """
    Diese Klasse enthält mathematische Hilfsfunktionen für die
    Transformation von 3D-Weltkoordinaten in 2D-Bildschirmkoordinaten.
    """

    @staticmethod
    def world_to_screen(view_matrix, world_pos, screen_width, screen_height):
        """
        Berechnet die Bildschirmposition aus einer 3D-Weltposition.
        Dies ist ein zentrales Konzept in der Computergrafik und im Reverse Engineering.
        """
        # Berechnung von W (Clip-Koordinate)
        w = view_matrix[12] * world_pos[0] + view_matrix[13] * world_pos[1] + view_matrix[14] * world_pos[2] + view_matrix[15]

        if w < 0.01:
            return None

        # Normalisierte Gerätekordinaten (NDC) im Bereich [-1, 1]
        x = (view_matrix[0] * world_pos[0] + view_matrix[1] * world_pos[1] + view_matrix[2] * world_pos[2] + view_matrix[3]) / w
        y = (view_matrix[4] * world_pos[0] + view_matrix[5] * world_pos[1] + view_matrix[6] * world_pos[2] + view_matrix[7]) / w

        # Umrechnung in Pixel-Koordinaten (Viewport-Transformation)
        screen_x = (x + 1.0) * screen_width / 2.0
        screen_y = (1.0 - y) * screen_height / 2.0

        return [screen_x, screen_y]

    @staticmethod
    def calculate_distance(pos1, pos2):
        """Berechnet die euklidische Distanz zwischen zwei Punkten in Units."""
        return np.linalg.norm(np.array(pos1) - np.array(pos2))

    @staticmethod
    def get_3d_box_corners(origin, min_h=-5, max_h=72, width=20):
        """
        Erzeugt die 8 Eckpunkte einer 3D-Box um eine Entity.
        Pädagogisch wertvoll für die Visualisierung von Volumina im Raum.
        """
        x, y, z = origin
        corners = [
            [x - width, y - width, z + min_h],
            [x + width, y - width, z + min_h],
            [x + width, y + width, z + min_h],
            [x - width, y + width, z + min_h],
            [x - width, y - width, z + max_h],
            [x + width, y - width, z + max_h],
            [x + width, y + width, z + max_h],
            [x - width, y + width, z + max_h]
        ]
        return corners
