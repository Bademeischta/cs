import dearpygui.dearpygui as dpg
import win32gui
import win32con
import win32api
import threading
import time

class VisualizerOverlay:
    """
    Diese Klasse erstellt ein transparentes Overlay-Fenster mit Dear PyGui.
    Sie nutzt die Windows-API für Transparenz und Click-Through Funktionalität.
    """

    def __init__(self, width=1920, height=1080):
        self.width = width
        self.height = height
        self.running = True
        self.render_data = [] # Liste von Objekten zum Zeichnen

    def create_overlay(self):
        dpg.create_context()
        dpg.create_viewport(title="EGMV Overlay",
                            width=self.width,
                            height=self.height,
                            always_on_top=True,
                            decorated=False,
                            clear_color=[0, 0, 0, 0]) # Alpha 0 für Transparenz

        # Erstellung des Zeichen-Fensters
        with dpg.window(label="Canvas", width=self.width, height=self.height, no_title_bar=True, no_resize=True, no_move=True, no_background=True) as self.canvas:
            dpg.add_draw_node(tag="draw_node")

        dpg.setup_dearpygui()
        dpg.show_viewport()

        # Windows API Aufrufe für Transparenz und Click-Through
        self._setup_transparency()

    def _setup_transparency(self):
        """Konfiguriert das Fenster so, dass es transparent und nicht interaktiv ist."""
        # Warten, bis das Fenster tatsächlich erstellt wurde
        hwnd = 0
        for _ in range(10):
            hwnd = win32gui.FindWindow(None, "EGMV Overlay")
            if hwnd: break
            time.sleep(0.1)

        if not hwnd:
            print("[Fehler] Overlay-Fenster konnte nicht gefunden werden.")
            return

        # Erweiterten Fensterstil setzen: Layered & Transparent (Click-Through)
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)

        # Schwarz (0,0,0) als transparente Farbe definieren
        win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(0, 0, 0), 0, win32con.LWA_COLORKEY)
        # Fenster in den Vordergrund bringen und Größe fixieren
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                             win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)

    def draw_2d_box(self, top_left, bottom_right, color=[255, 255, 255, 255], thickness=1):
        dpg.draw_rectangle(top_left, bottom_right, color=color, thickness=thickness, parent="draw_node")

    def draw_3d_box(self, screen_corners, color=[255, 255, 255, 255], thickness=1):
        """Verbindet die 8 Eckpunkte einer 3D-Box mit Linien."""
        # Untere Ebene
        for i in range(4):
            self.draw_line(screen_corners[i], screen_corners[(i+1)%4], color, thickness)
        # Obere Ebene
        for i in range(4, 8):
            self.draw_line(screen_corners[i], screen_corners[4 + (i+1)%4], color, thickness)
        # Verbindungen
        for i in range(4):
            self.draw_line(screen_corners[i], screen_corners[i+4], color, thickness)

    def draw_line(self, start, end, color=[255, 255, 255, 255], thickness=1):
        dpg.draw_line(start, end, color=color, thickness=thickness, parent="draw_node")

    def draw_text(self, pos, text, color=[255, 255, 255, 255], size=14):
        dpg.draw_text(pos, text, color=color, size=size, parent="draw_node")

    def draw_health_bar(self, pos, health, max_health=100):
        """Visualisiert die Gesundheit als vertikalen Balken."""
        height = 50
        width = 4
        fill_height = (health / max_health) * height

        # Hintergrund (Grau)
        dpg.draw_rectangle([pos[0], pos[1]], [pos[0] + width, pos[1] + height], fill=[50, 50, 50, 200], color=[0, 0, 0, 255], parent="draw_node")
        # Vordergrund (Grün/Rot je nach Health)
        color = [int(255 * (1 - health/100)), int(255 * (health/100)), 0, 255]
        dpg.draw_rectangle([pos[0], pos[1] + (height - fill_height)], [pos[0] + width, pos[1] + height], fill=color, color=[0,0,0,0], parent="draw_node")

    def clear(self):
        dpg.delete_item("draw_node")
        dpg.add_draw_node(tag="draw_node", parent=self.canvas)

    def update(self):
        if dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
        else:
            self.running = False

    def close(self):
        dpg.destroy_context()
