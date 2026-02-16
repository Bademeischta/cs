"""
================================================================================
Educational Game Memory Visualizer (EGMV) - Version 1.0
================================================================================
Dieses Tool wurde ausschließlich zu Lehrzwecken für Universitätskurse im Fach
„Reverse Engineering & Memory Management“ entwickelt. Es demonstriert, wie
externe Datenvisualisierung (Overlay) durch das Lesen von Prozess-Speicher
funktioniert.

WIE MAN DAS TOOL STARTET:
1. Installieren Sie Python 3.10 oder höher.
2. Installieren Sie die benötigten Bibliotheken:
   pip install pymem dearpygui pywin32 numpy
3. Stellen Sie sicher, dass CS2 (cs2.exe) im Fenstermodus oder
   "Vollbild im Fenstermodus" läuft.
4. Aktualisieren Sie die Offsets in der 'config.ini' mit aktuellen Werten
   (z.B. von a2x's CS2-Dumper oder ähnlichen Quellen).
5. Starten Sie dieses Skript mit Administratorrechten (wegen OpenProcess-Berechtigungen):
   python main.py

PÄDAGOGISCHE HINWEISE:
- Das Tool nutzt 'ReadProcessMemory' (via pymem). Es führt keine Schreiboperationen durch.
- Die World-To-Screen Transformation nutzt die im Speicher liegende ViewMatrix.
- Das Skeleton-Rendering (Bones) zeigt die hierarchische Struktur von Spielfiguren.
- Zufällige Verzögerungen demonstrieren Techniken zur Reduzierung der Systemlast
  und zur Vermeidung von signaturbasierten Analysen.
================================================================================
"""

import threading
import time
import random
from memory_manager import MemoryManager
from math_engine import MathEngine
from visualizer_overlay import VisualizerOverlay
import win32api
import win32con

class EGMV_App:
    def __init__(self):
        self.mem = MemoryManager()
        self.math = MathEngine()
        # Standard Auflösung (sollte idealerweise automatisch erkannt werden)
        self.screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        self.screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        self.overlay = VisualizerOverlay(self.screen_width, self.screen_height)

        self.entities_data = []
        self.lock = threading.Lock()
        self.running = True

    def memory_reader_thread(self):
        """
        Separater Thread für das Auslesen des Speichers.
        Dies verhindert Ruckler in der UI und zeigt das Konzept von asynchronem Memory-Parsing.
        """
        if not self.mem.initialize():
            self.running = False
            return

        while self.running:
            try:
                local_player = self.mem.get_local_player()
                if not local_player:
                    time.sleep(1)
                    continue

                local_team = self.mem.read_int(local_player + self.mem.offsets['m_iTeamNum'])
                view_matrix = self.mem.get_view_matrix()

                temp_entities = []

                # Wir iterieren über eine begrenzte Anzahl von Entity-Slots (Pädagogisch: 1 bis 64)
                for i in range(1, 64):
                    pawn_ptr, controller_ptr = self.mem.get_player_data(i)
                    if not pawn_ptr or pawn_ptr == local_player:
                        continue

                    # Basis-Filterung: Nur Gegner anzeigen
                    team = self.mem.read_int(pawn_ptr + self.mem.offsets['m_iTeamNum'])
                    if team == local_team:
                        continue

                    health = self.mem.read_int(pawn_ptr + self.mem.offsets['m_iHealth'])
                    if health <= 0 or health > 100:
                        continue

                    origin = self.mem.read_vec3(pawn_ptr + self.mem.offsets['m_vOldOrigin'])
                    name = self.mem.read_string(controller_ptr + self.mem.offsets['m_iszPlayerName'])

                    # Bone-Position für 3D-Box (Kopf-Position schätzen oder auslesen)
                    head_pos = self.mem.get_bone_position(pawn_ptr, 6) # Index 6 ist oft der Kopf

                    temp_entities.append({
                        'origin': origin,
                        'head_pos': head_pos,
                        'health': health,
                        'name': name,
                        'distance': self.math.calculate_distance(self.mem.read_vec3(local_player + self.mem.offsets['m_vOldOrigin']), origin)
                    })

                with self.lock:
                    self.entities_data = temp_entities
                    self.current_view_matrix = view_matrix

                # Pädagogisches Delay zur Schonung der Ressourcen
                self.mem.apply_stealth_delay()

            except Exception as e:
                print(f"[Fehler im Reader] {e}")
                time.sleep(1)

    def run(self):
        # Start des Speicher-Lese-Threads
        reader = threading.Thread(target=self.memory_reader_thread, daemon=True)
        reader.start()

        # Initialisierung des Overlays
        self.overlay.create_overlay()

        # Haupt-UI-Loop
        while self.overlay.running and self.running:
            self.overlay.clear()

            with self.lock:
                data = self.entities_data
                matrix = getattr(self, 'current_view_matrix', None)

            if matrix:
                for ent in data:
                    # World-To-Screen Transformation für die Füße
                    screen_pos = self.math.world_to_screen(matrix, ent['origin'], self.screen_width, self.screen_height)

                    if screen_pos:
                        # Snaplines vom Fadenkreuz (Bildschirmmitte)
                        if self.mem.config['Visuals'].getboolean('ShowSnaplines'):
                            self.overlay.draw_line([self.screen_width/2, self.screen_height/2], screen_pos, color=[200, 200, 200, 150])

                        # 2D/3D Box Logik
                        if ent['head_pos']:
                            head_screen = self.math.world_to_screen(matrix, ent['head_pos'], self.screen_width, self.screen_height)
                            if head_screen:
                                h = abs(screen_pos[1] - head_screen[1])
                                w = h / 2

                                # 2D Box
                                if self.mem.config['Visuals'].getboolean('Show2DBox'):
                                    self.overlay.draw_2d_box([screen_pos[0] - w/2, head_screen[1]], [screen_pos[0] + w/2, screen_pos[1]], color=[255, 0, 0, 255])

                                # 3D Box
                                if self.mem.config['Visuals'].getboolean('Show3DBox'):
                                    corners_3d = self.math.get_3d_box_corners(ent['origin'])
                                    screen_corners = []
                                    for c in corners_3d:
                                        sc = self.math.world_to_screen(matrix, c, self.screen_width, self.screen_height)
                                        if sc: screen_corners.append(sc)

                                    if len(screen_corners) == 8:
                                        self.overlay.draw_3d_box(screen_corners, color=[255, 0, 0, 255])

                                if self.mem.config['Visuals'].getboolean('ShowHealthBar'):
                                    self.overlay.draw_health_bar([screen_pos[0] - w/2 - 6, head_screen[1]], ent['health'])

                                if self.mem.config['Visuals'].getboolean('ShowNameTag'):
                                    self.overlay.draw_text([screen_pos[0] - w/2, head_screen[1] - 15], ent['name'], color=[255, 255, 255, 255])

                        # Distanz-Anzeige
                        if self.mem.config['Visuals'].getboolean('ShowDistance'):
                            dist_m = int(ent['distance'] * 0.0254) # Umrechnung Units in Meter (ca.)
                            self.overlay.draw_text([screen_pos[0], screen_pos[1] + 5], f"{dist_m}m", color=[255, 255, 255, 255])

            self.overlay.update()

        self.running = False
        self.overlay.close()

if __name__ == "__main__":
    app = EGMV_App()
    app.run()
