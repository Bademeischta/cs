import pymem
import pymem.process
import time
import random
import configparser
import struct

class MemoryManager:
    """
    Diese Klasse verwaltet den Zugriff auf den Arbeitsspeicher des Zielprozesses.
    Sie demonstriert die Verwendung von ReadProcessMemory (via pymem) und
    pädagogisch wertvolle Konzepte wie Pattern-Scanning und Lese-Verzögerungen.
    """

    def __init__(self, config_path='config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)

        self.process_name = self.config['Process']['TargetProcess']
        self.pm = None
        self.client_base = None

        # Offsets aus der Config laden
        self.offsets = {
            'dwLocalPlayerPawn': int(self.config['Offsets']['dwLocalPlayerPawn'], 16),
            'dwEntityList': int(self.config['Offsets']['dwEntityList'], 16),
            'dwViewMatrix': int(self.config['Offsets']['dwViewMatrix'], 16),
            'm_iHealth': int(self.config['Offsets']['m_iHealth'], 16),
            'm_iTeamNum': int(self.config['Offsets']['m_iTeamNum'], 16),
            'm_vOldOrigin': int(self.config['Offsets']['m_vOldOrigin'], 16),
            'm_pGameSceneNode': int(self.config['Offsets']['m_pGameSceneNode'], 16),
            'm_modelState': int(self.config['Offsets']['m_modelState'], 16),
            'm_hPlayerPawn': int(self.config['Offsets']['m_hPlayerPawn'], 16),
            'm_iszPlayerName': int(self.config['Offsets']['m_iszPlayerName'], 16),
        }

    def initialize(self):
        """Versucht, sich an den Prozess zu hängen und die Basisadresse zu finden."""
        try:
            self.pm = pymem.Pymem(self.process_name)
            self.client_base = pymem.process.module_from_name(self.pm.process_handle, "client.dll").lpBaseOfDll
            print(f"[Info] Erfolgreich an {self.process_name} angehängt. client.dll @ {hex(self.client_base)}")
            return True
        except Exception as e:
            print(f"[Fehler] Konnte Prozess nicht finden: {e}")
            return False

    def scan_pattern(self, pattern, module_name="client.dll"):
        """
        Demonstriert 'Signature-less' Pattern Scanning.
        Sucht nach einer Byte-Folge im Speicher eines Moduls.
        """
        try:
            module = pymem.process.module_from_name(self.pm.process_handle, module_name)
            address = pymem.pattern.pattern_scan_module(self.pm.process_handle, module, pattern.encode())
            if address:
                # Pädagogischer Hinweis: Oft muss hier noch ein Offset addiert oder
                # eine relative Adresse (RIP-relative) aufgelöst werden.
                return address
            return None
        except Exception as e:
            print(f"[Fehler] Pattern Scan fehlgeschlagen: {e}")
            return None

    def read_string(self, address, length=32):
        """Liest einen Null-terminierten String aus dem Speicher."""
        try:
            data = self.pm.read_bytes(address, length)
            # Finde Null-Terminator
            end = data.find(b'\x00')
            if end != -1:
                return data[:end].decode('utf-8', errors='ignore')
            return data.decode('utf-8', errors='ignore')
        except:
            return "Unknown"

    def read_float(self, address):
        return self.pm.read_float(address)

    def read_int(self, address):
        return self.pm.read_int(address)

    def read_vec3(self, address):
        """Liest drei aufeinanderfolgende Floats (X, Y, Z)."""
        data = self.pm.read_bytes(address, 12)
        return struct.unpack('fff', data)

    def get_local_player(self):
        """Liest die Basisadresse des lokalen Spielers (Pawn)."""
        return self.pm.read_longlong(self.client_base + self.offsets['dwLocalPlayerPawn'])

    def get_view_matrix(self):
        """Liest die 4x4 View-Matrix für die World-To-Screen Transformation."""
        view_matrix_addr = self.client_base + self.offsets['dwViewMatrix']
        data = self.pm.read_bytes(view_matrix_addr, 64)
        return struct.unpack('16f', data)

    def get_entity_list(self):
        """Gibt die Basisadresse der Entity-Liste zurück."""
        return self.pm.read_longlong(self.client_base + self.offsets['dwEntityList'])

    def get_player_data(self, index):
        """
        Pädagogisches Beispiel für das Traversieren der CS2 Entity-Liste.
        Gibt sowohl Controller- als auch Pawn-Informationen zurück.
        """
        try:
            ent_list = self.get_entity_list()
            # Bestimmung des Chunks für den Controller
            list_entry = self.pm.read_longlong(ent_list + (8 * (index & 0x7FFF) >> 9) + 16)
            if not list_entry:
                return None, None

            # Bestimmung des Controllers
            player_controller = self.pm.read_longlong(list_entry + 120 * (index & 0x1FF))
            if not player_controller:
                return None, None

            # Auslesen des Pawns aus dem Controller
            pawn_handle = self.pm.read_int(player_controller + self.offsets['m_hPlayerPawn'])
            if not pawn_handle:
                return None, player_controller

            # Zugriff auf den Pawn über die Entity-Liste
            list_entry_pawn = self.pm.read_longlong(ent_list + (8 * (pawn_handle & 0x7FFF) >> 9) + 16)
            if not list_entry_pawn:
                return None, player_controller

            pawn_ptr = self.pm.read_longlong(list_entry_pawn + 120 * (pawn_handle & 0x1FF))
            return pawn_ptr, player_controller
        except:
            return None, None

    def get_bone_position(self, pawn_ptr, bone_index):
        """
        Liest die Position eines spezifischen Skelett-Punkts (Bone).
        Dies zeigt den Studenten, wie komplexe Animation-Strukturen aufgebaut sind.
        """
        try:
            game_scene_node = self.pm.read_longlong(pawn_ptr + self.offsets['m_pGameSceneNode'])
            bone_array_ptr = self.pm.read_longlong(game_scene_node + self.offsets['m_modelState'] + 0x80) # BoneArray Offset

            # Jeder Bone besteht oft aus 32 Bytes (Transform Matrix oder Vec3 + Padding)
            bone_addr = bone_array_ptr + (bone_index * 32)
            return self.read_vec3(bone_addr)
        except:
            return None

    def apply_stealth_delay(self):
        """
        Simuliert eine Erkennungs-Vermeidungs-Strategie durch zufällige Lese-Intervalle.
        """
        delay = random.uniform(
            float(self.config['Visuals']['RenderDelayMin']),
            float(self.config['Visuals']['RenderDelayMax'])
        )
        time.sleep(delay)
