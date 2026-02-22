#!/usr/bin/env python3
"""
Whisper PTT – GUI Edition v5
==============================
  • Multilingual UI: English (default), Deutsch, Français, Español
  • UI language selector in Settings → General
  • Mic-Watchdog: auto-restart on silent inputs after reboot
  • Windows mic permission request (winrt / registry / privacy settings)
  • Always-on-top overlay, voice meter, dual text panels
  • Hotkey recorder supports keyboard AND mouse buttons (pynput)
"""

VERSION = "0.6.0"

import os, sys, time, json, tempfile, threading, queue, subprocess, ctypes
import numpy as np
import sounddevice as sd
import soundfile as sf
import pyperclip
import pyautogui
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from pynput import keyboard as pynput_kb
from pynput import mouse    as pynput_ms

# ─── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR        = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
SETTINGS_FILE   = BASE_DIR / "settings.json"
MODEL_CACHE_DIR = str(BASE_DIR / "models")

# ─── Defaults ──────────────────────────────────────────────────────────────────

DEFAULTS = {
    "hotkey":          "ctrl+alt+space",
    "language":        "de",        # Whisper recognition language
    "ui_lang":         "en",        # Interface language
    "model":           "base",
    "device":          "auto",
    "compute_type":    "auto",
    "paste_mode":      "clipboard",
    "output_language": "same",   # "same" = no translation, "en" = translate to English
    "vad_filter":      True,
    "vad_silence_ms":  300,
    "sound_feedback":  True,
    "opacity":         0.95,
    "beam_size":       5,
    "window_x":        -1,
    "window_y":        -1,
}

# ─── Colors ────────────────────────────────────────────────────────────────────

C = {
    "bg":         "#1a1a2e", "bg2": "#16213e", "bg3": "#0d0d1a",
    "accent":     "#0f3460", "accent2": "#1a4a8a",
    "idle":       "#4a4a6a", "record": "#e94560",
    "process":    "#f5a623", "ready": "#00d4aa",
    "text":       "#e0e0e0", "dim": "#888899",
    "meter_low":  "#00d4aa", "meter_mid": "#f5a623", "meter_high": "#e94560",
    "btn_copy":   "#0f3460", "btn_paste": "#1a6b3c",
    "btn_clear":  "#3d1a1a", "btn_set": "#2a2a4a", "sep": "#333355",
}

# ─── Translations ──────────────────────────────────────────────────────────────

TRANSLATIONS = {
    # ── Status messages ────────────────────────────────────────────────────────
    "initializing": {
        "en": "Initializing...", "de": "Initialisiere...",
        "fr": "Initialisation...", "es": "Inicializando...",
    },
    "recording": {
        "en": "Recording...", "de": "Aufnahme...",
        "fr": "Enregistrement...", "es": "Grabando...",
    },
    "processing": {
        "en": "Processing...", "de": "Verarbeite...",
        "fr": "Traitement...", "es": "Procesando...",
    },
    "ready": {
        "en": "Ready", "de": "Bereit",
        "fr": "Prêt", "es": "Listo",
    },
    "mic_error": {
        "en": "Mic error!", "de": "Mic-Fehler!",
        "fr": "Erreur micro!", "es": "¡Error mic!",
    },
    "mic_restart": {
        "en": "Mic restart...", "de": "Mic Neustart...",
        "fr": "Redémarrage micro...", "es": "Reiniciando mic...",
    },
    "load_error": {
        "en": "Load error!", "de": "Ladefehler!",
        "fr": "Erreur chargement!", "es": "¡Error de carga!",
    },
    # ── Overlay labels ─────────────────────────────────────────────────────────
    "microphone": {
        "en": "MICROPHONE", "de": "MIKROFON",
        "fr": "MICROPHONE", "es": "MICRÓFONO",
    },
    "recognized_text": {
        "en": "RECOGNIZED TEXT", "de": "ERKANNTER TEXT",
        "fr": "TEXTE RECONNU", "es": "TEXTO RECONOCIDO",
    },
    "debug_log": {
        "en": "DEBUG / LOG", "de": "DEBUG / LOG",
        "fr": "DEBUG / JOURNAL", "es": "DEBUG / LOG",
    },
    # ── Overlay buttons ────────────────────────────────────────────────────────
    "btn_copy": {
        "en": "📋 Copy", "de": "📋 Kopieren",
        "fr": "📋 Copier", "es": "📋 Copiar",
    },
    "btn_paste": {
        "en": "📌 Paste", "de": "📌 Einfügen",
        "fr": "📌 Coller", "es": "📌 Pegar",
    },
    "btn_clear": {
        "en": "🗑️ Clear", "de": "🗑️ Leeren",
        "fr": "🗑️ Effacer", "es": "🗑️ Limpiar",
    },
    "btn_clear_log": {
        "en": "🗑️ Clear log", "de": "🗑️ Log leeren",
        "fr": "🗑️ Vider journal", "es": "🗑️ Limpiar log",
    },
    "flash_copied": {
        "en": "📋 Copied!", "de": "📋 Kopiert!",
        "fr": "📋 Copié!", "es": "📋 ¡Copiado!",
    },
    "flash_pasted": {
        "en": "📌 Pasted!", "de": "📌 Eingefügt!",
        "fr": "📌 Collé!", "es": "📌 ¡Pegado!",
    },
    # ── Settings window ────────────────────────────────────────────────────────
    "settings_title": {
        "en": "⚙  Settings", "de": "⚙  Einstellungen",
        "fr": "⚙  Paramètres", "es": "⚙  Ajustes",
    },
    "settings_win_title": {
        "en": "Settings – Whisper PTT", "de": "Einstellungen – Whisper PTT",
        "fr": "Paramètres – Whisper PTT", "es": "Ajustes – Whisper PTT",
    },
    "tab_general": {
        "en": "  General  ", "de": "  Allgemein  ",
        "fr": "  Général  ", "es": "  General  ",
    },
    "tab_audio": {
        "en": "  Audio / AI  ", "de": "  Audio / KI  ",
        "fr": "  Audio / IA  ", "es": "  Audio / IA  ",
    },
    "tab_advanced": {
        "en": "  Advanced  ", "de": "  Erweitert  ",
        "fr": "  Avancé  ", "es": "  Avanzado  ",
    },
    "btn_save": {
        "en": "✔  Save", "de": "✔  Speichern",
        "fr": "✔  Enregistrer", "es": "✔  Guardar",
    },
    "btn_cancel": {
        "en": "Cancel", "de": "Abbrechen",
        "fr": "Annuler", "es": "Cancelar",
    },
    "checking_hw": {
        "en": "Checking hardware...", "de": "Prüfe Hardware...",
        "fr": "Vérification matériel...", "es": "Comprobando hardware...",
    },
    # ── Settings sections ──────────────────────────────────────────────────────
    "sec_hotkey": {
        "en": "Shortcut / Mouse Button (Hotkey)",
        "de": "Tastenkürzel / Maustaste (Hotkey)",
        "fr": "Raccourci / Bouton souris (Hotkey)",
        "es": "Atajo / Botón ratón (Hotkey)",
    },
    "hotkey_hint": {
        "en": "Keyboard keys AND mouse buttons (e.g. thumb button) are supported.",
        "de": "Keyboard-Tasten UND Maustasten (z.B. Daumentaste) werden erkannt.",
        "fr": "Les touches clavier ET les boutons souris (ex. pouce) sont supportés.",
        "es": "Teclas de teclado Y botones de ratón (p.ej. pulgar) son compatibles.",
    },
    "btn_record": {
        "en": "🔴 Record", "de": "🔴 Aufnehmen",
        "fr": "🔴 Enregistrer", "es": "🔴 Grabar",
    },
    "btn_stop_record": {
        "en": "⏹  Stop", "de": "⏹  Stoppen",
        "fr": "⏹  Arrêter", "es": "⏹  Detener",
    },
    "recorder_hint": {
        "en": "Press modifier (Ctrl/Alt) + key OR mouse button",
        "de": "Modifier (Ctrl/Alt) + Taste ODER Maustaste drücken",
        "fr": "Appuyer modificateur (Ctrl/Alt) + touche OU bouton souris",
        "es": "Pulsar modificador (Ctrl/Alt) + tecla O botón de ratón",
    },
    "recorder_prompt": {
        "en": "▶  Press keys / mouse button ...",
        "de": "▶  Tasten / Maustaste drücken ...",
        "fr": "▶  Appuyez touches / bouton souris ...",
        "es": "▶  Pulsa teclas / botón ratón ...",
    },
    "sec_ui_lang": {
        "en": "Interface Language",
        "de": "Oberflächensprache",
        "fr": "Langue de l'interface",
        "es": "Idioma de la interfaz",
    },
    "ui_lang_note": {
        "en": "Restart required to apply interface language change.",
        "de": "Neustart erforderlich um die Sprachänderung anzuwenden.",
        "fr": "Redémarrage requis pour appliquer le changement de langue.",
        "es": "Se requiere reinicio para aplicar el cambio de idioma.",
    },
    "sec_rec_lang": {
        "en": "Recognition Language (Input)",
        "de": "Erkennungssprache (Eingabe)",
        "fr": "Langue de reconnaissance (entrée)",
        "es": "Idioma de reconocimiento (entrada)",
    },
    "sec_output_lang": {
        "en": "Output Language / Translation",
        "de": "Ausgabesprache / Übersetzung",
        "fr": "Langue de sortie / Traduction",
        "es": "Idioma de salida / Traducción",
    },
    "output_same": {
        "en": "Same as input (no translation)",
        "de": "Wie Eingabe (keine Übersetzung)",
        "fr": "Comme l'entrée (sans traduction)",
        "es": "Igual que la entrada (sin traducción)",
    },
    "output_lang_note": {
        "en": "Whisper can only translate to English natively.",
        "de": "Whisper kann nativ nur ins Englische übersetzen.",
        "fr": "Whisper ne peut traduire nativement qu'en anglais.",
        "es": "Whisper solo puede traducir al inglés de forma nativa.",
    },
    "sec_paste": {
        "en": "Insert text via",
        "de": "Text einfügen via",
        "fr": "Insérer le texte via",
        "es": "Insertar texto via",
    },
    "paste_clipboard": {
        "en": "Clipboard (Ctrl+V)  ← recommended",
        "de": "Zwischenablage (Ctrl+V)  ← empfohlen",
        "fr": "Presse-papiers (Ctrl+V)  ← recommandé",
        "es": "Portapapeles (Ctrl+V)  ← recomendado",
    },
    "paste_type": {
        "en": "Direct typing (no clipboard, but slower)",
        "de": "Direkt tippen (kein Clipboard, aber langsamer)",
        "fr": "Saisie directe (sans presse-papiers, plus lent)",
        "es": "Escritura directa (sin portapapeles, más lento)",
    },
    "sec_appearance": {
        "en": "Appearance",
        "de": "Erscheinungsbild",
        "fr": "Apparence",
        "es": "Apariencia",
    },
    "sound_feedback": {
        "en": "Audio feedback (beep on start/stop)",
        "de": "Audio-Feedback (Beep bei Start/Stop)",
        "fr": "Retour audio (bip au démarrage/arrêt)",
        "es": "Retroalimentación audio (pitido al inicio/fin)",
    },
    "transparency": {
        "en": "Transparency:",
        "de": "Transparenz:",
        "fr": "Transparence:",
        "es": "Transparencia:",
    },
    "sec_device": {
        "en": "Compute Device",
        "de": "Berechnungsgerät",
        "fr": "Périphérique de calcul",
        "es": "Dispositivo de cálculo",
    },
    "sec_compute": {
        "en": "Compute Type",
        "de": "Compute-Typ",
        "fr": "Type de calcul",
        "es": "Tipo de cálculo",
    },
    "compute_note": {
        "en": "'Auto' selects the optimal type for the device.",
        "de": "'Auto' wählt automatisch den optimalen Typ je nach Gerät.",
        "fr": "'Auto' sélectionne le type optimal pour le périphérique.",
        "es": "'Auto' selecciona el tipo óptimo para el dispositivo.",
    },
    "sec_model": {
        "en": "Whisper Model",
        "de": "Whisper-Modell",
        "fr": "Modèle Whisper",
        "es": "Modelo Whisper",
    },
    "sec_vad": {
        "en": "Voice Activity Detection (VAD)",
        "de": "Voice Activity Detection (VAD)",
        "fr": "Détection d'activité vocale (VAD)",
        "es": "Detección de actividad de voz (VAD)",
    },
    "vad_enable": {
        "en": "Enable VAD (automatically ignores silence)",
        "de": "VAD aktivieren (ignoriert Stille automatisch)",
        "fr": "Activer VAD (ignore automatiquement le silence)",
        "es": "Activar VAD (ignora el silencio automáticamente)",
    },
    "vad_threshold": {
        "en": "Silence threshold:",
        "de": "Stille-Schwelle:",
        "fr": "Seuil de silence:",
        "es": "Umbral de silencio:",
    },
    "sec_beam": {
        "en": "Beam Size  (quality vs. speed)",
        "de": "Beam Size  (Qualität vs. Geschwindigkeit)",
        "fr": "Beam Size  (qualité vs. vitesse)",
        "es": "Beam Size  (calidad vs. velocidad)",
    },
    "beam_hint": {
        "en": "(1=fast, 5=default, 10=accurate)",
        "de": "(1=schnell, 5=Standard, 10=genau)",
        "fr": "(1=rapide, 5=défaut, 10=précis)",
        "es": "(1=rápido, 5=defecto, 10=preciso)",
    },
    "btn_reset": {
        "en": "↺  Reset all settings to defaults",
        "de": "↺  Alle Einstellungen auf Standard zurücksetzen",
        "fr": "↺  Réinitialiser tous les paramètres",
        "es": "↺  Restablecer todos los ajustes",
    },
    "reset_confirm_title": {
        "en": "Reset", "de": "Zurücksetzen",
        "fr": "Réinitialiser", "es": "Restablecer",
    },
    "reset_confirm_msg": {
        "en": "Reset all settings to defaults?",
        "de": "Alle Einstellungen zurücksetzen?",
        "fr": "Réinitialiser tous les paramètres?",
        "es": "¿Restablecer todos los ajustes?",
    },
    # ── Model descriptions ─────────────────────────────────────────────────────
    "model_tiny": {
        "en": "~75 MB   | very fast   | simple text",
        "de": "~75 MB   | sehr schnell | einfacher Text",
        "fr": "~75 MB   | très rapide  | texte simple",
        "es": "~75 MB   | muy rápido   | texto simple",
    },
    "model_base": {
        "en": "~150 MB  | fast        | good for everyday use  ★",
        "de": "~150 MB  | schnell      | gut für Alltag  ★",
        "fr": "~150 MB  | rapide       | bon usage quotidien  ★",
        "es": "~150 MB  | rápido       | bueno para el día a día  ★",
    },
    "model_small": {
        "en": "~500 MB  | medium      | better accuracy",
        "de": "~500 MB  | mittel       | bessere Genauigkeit",
        "fr": "~500 MB  | moyen        | meilleure précision",
        "es": "~500 MB  | medio        | mayor precisión",
    },
    "model_medium": {
        "en": "~1.5 GB  | slow        | high accuracy",
        "de": "~1.5 GB  | langsam      | hohe Genauigkeit",
        "fr": "~1.5 GB  | lent         | haute précision",
        "es": "~1.5 GB  | lento        | alta precisión",
    },
    "model_large_v2": {
        "en": "~3 GB    | very slow   | maximum accuracy",
        "de": "~3 GB    | sehr langsam | maximale Genauigkeit",
        "fr": "~3 GB    | très lent    | précision maximale",
        "es": "~3 GB    | muy lento    | precisión máxima",
    },
    "model_large_v3": {
        "en": "~3 GB    | very slow   | latest version",
        "de": "~3 GB    | sehr langsam | neueste Version",
        "fr": "~3 GB    | très lent    | dernière version",
        "es": "~3 GB    | muy lento    | última versión",
    },
    # ── Hardware detection strings ─────────────────────────────────────────────
    "hw_not_available": {
        "en": "not available", "de": "nicht verfügbar",
        "fr": "non disponible", "es": "no disponible",
    },
    "hw_available": {
        "en": "available", "de": "verfügbar",
        "fr": "disponible", "es": "disponible",
    },
    # ── Mic permission dialog ──────────────────────────────────────────────────
    "mic_perm_title": {
        "en": "Microphone Permission",
        "de": "Mikrofon-Berechtigung",
        "fr": "Permission microphone",
        "es": "Permiso micrófono",
    },
    "mic_perm_msg": {
        "en": (
            "Windows Microphone Settings have been opened.\n\n"
            "1. Make sure 'Microphone access' is enabled\n"
            "2. Enable 'Allow apps to access your microphone'\n"
            "3. Close that window\n"
            "4. Click 🎤↺ to restart the microphone"
        ),
        "de": (
            "Windows Mikrofon-Einstellungen wurden geöffnet.\n\n"
            "1. Sicherstellen dass 'Mikrofon-Zugriff' aktiviert ist\n"
            "2. 'Apps Zugriff auf Ihr Mikrofon erlauben' aktivieren\n"
            "3. Dieses Fenster schließen\n"
            "4. Auf 🎤↺ klicken um das Mikrofon neu zu starten"
        ),
        "fr": (
            "Les paramètres du microphone Windows ont été ouverts.\n\n"
            "1. S'assurer que 'Accès au microphone' est activé\n"
            "2. Activer 'Autoriser les applis à accéder au microphone'\n"
            "3. Fermer cette fenêtre\n"
            "4. Cliquer sur 🎤↺ pour redémarrer le microphone"
        ),
        "es": (
            "Se han abierto los ajustes del micrófono de Windows.\n\n"
            "1. Asegurarse de que 'Acceso al micrófono' está activado\n"
            "2. Activar 'Permitir a las apps acceder al micrófono'\n"
            "3. Cerrar esa ventana\n"
            "4. Hacer clic en 🎤↺ para reiniciar el micrófono"
        ),
    },
    # ── Log messages (keep short) ──────────────────────────────────────────────
    "log_no_signal": {
        "en": "No mic signal", "de": "Kein Mic-Signal",
        "fr": "Pas de signal micro", "es": "Sin señal de mic",
    },
    "log_restarting": {
        "en": "Restarting mic (too many silent recordings)...",
        "de": "Starte Mikrofon-Neustart (zu viele stille Aufnahmen)...",
        "fr": "Redémarrage micro (trop d'enregistrements silencieux)...",
        "es": "Reiniciando mic (demasiadas grabaciones silenciosas)...",
    },
    "log_too_short": {
        "en": "Recording too short – ignored.",
        "de": "Aufnahme zu kurz – ignoriert.",
        "fr": "Enregistrement trop court – ignoré.",
        "es": "Grabación demasiada corta – ignorada.",
    },
    "log_no_text": {
        "en": "No text recognized.",
        "de": "Kein Text erkannt.",
        "fr": "Aucun texte reconnu.",
        "es": "No se reconoció texto.",
    },
}

# UI language options shown in the dropdown
UI_LANGUAGES = {
    "English":  "en",
    "Deutsch":  "de",
    "Français": "fr",
    "Español":  "es",
}

# Whisper recognition language options (language-code only, labels built per UI lang below)
RECOG_LANGUAGES_CODES = {
    "auto": None, "de": "de", "en": "en", "fr": "fr", "es": "es",
    "it": "it", "nl": "nl", "pl": "pl", "ru": "ru",
    "zh": "zh", "ja": "ja", "tr": "tr",
}

def _recog_lang_labels(ui: str) -> dict:
    """Return recognition language labels in the current UI language."""
    labels = {
        "en": {
            "auto": "Auto-detect", "de": "German", "en": "English",
            "fr": "French", "es": "Spanish", "it": "Italian",
            "nl": "Dutch", "pl": "Polish", "ru": "Russian",
            "zh": "Chinese", "ja": "Japanese", "tr": "Turkish",
        },
        "de": {
            "auto": "Automatisch", "de": "Deutsch", "en": "Englisch",
            "fr": "Französisch", "es": "Spanisch", "it": "Italienisch",
            "nl": "Niederländisch", "pl": "Polnisch", "ru": "Russisch",
            "zh": "Chinesisch", "ja": "Japanisch", "tr": "Türkisch",
        },
        "fr": {
            "auto": "Automatique", "de": "Allemand", "en": "Anglais",
            "fr": "Français", "es": "Espagnol", "it": "Italien",
            "nl": "Néerlandais", "pl": "Polonais", "ru": "Russe",
            "zh": "Chinois", "ja": "Japonais", "tr": "Turc",
        },
        "es": {
            "auto": "Automático", "de": "Alemán", "en": "Inglés",
            "fr": "Francés", "es": "Español", "it": "Italiano",
            "nl": "Holandés", "pl": "Polaco", "ru": "Ruso",
            "zh": "Chino", "ja": "Japonés", "tr": "Turco",
        },
    }
    return labels.get(ui, labels["en"])

MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
DEVICES = {"auto": "Auto", "cuda": "NVIDIA CUDA", "dml": "NPU / DirectML", "cpu": "CPU"}
COMPUTE_TYPES = {"auto": "Auto", "float16": "float16 (GPU)", "int8": "int8", "float32": "float32 (CPU)"}

MOUSE_BTN_NAMES = {
    pynput_ms.Button.left:   "mouse_left",
    pynput_ms.Button.right:  "mouse_right",
    pynput_ms.Button.middle: "mouse_middle",
    pynput_ms.Button.x1:     "mouse_x1",
    pynput_ms.Button.x2:     "mouse_x2",
}

# ─── Global State ───────────────────────────────────────────────────────────────

recording       = False
audio_chunks    = []
record_lock     = threading.Lock()
whisper_model   = None
current_volume  = 0.0
ui_queue        = queue.Queue()
cfg             = dict(DEFAULTS)

_ptt_kb_listener = None
_ptt_ms_listener = None
_ptt_active      = False

_silent_count    = 0
SILENT_THRESHOLD = 3
MIC_OK           = True
_audio_stream    = None

# ─── Translation helper ────────────────────────────────────────────────────────

def T(key: str, lang: str = None) -> str:
    """Return translated string for current UI language."""
    l = lang or cfg.get("ui_lang", "en")
    entry = TRANSLATIONS.get(key, {})
    return entry.get(l, entry.get("en", key))

# ─── Settings ──────────────────────────────────────────────────────────────────

def load_settings():
    global cfg
    cfg = dict(DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass

def save_settings():
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Settings error: {e}")

# ─── Hardware detection ────────────────────────────────────────────────────────

def detect_devices() -> dict:
    r = {"cuda": False, "dml": False, "cuda_name": "", "npu_name": ""}
    try:
        import torch
        if torch.cuda.is_available():
            r["cuda"] = True; r["cuda_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    try:
        import openvino as ov
        devs = ov.Core().available_devices
        if any("NPU" in d for d in devs):
            r["dml"] = True; r["npu_name"] = next(d for d in devs if "NPU" in d)
    except Exception:
        pass
    try:
        import onnxruntime as ort
        if "DmlExecutionProvider" in ort.get_available_providers():
            r["dml"] = True; r["npu_name"] = r["npu_name"] or "DirectML"
    except Exception:
        pass
    return r

def resolve_device(dev_cfg, compute_cfg):
    av = detect_devices()
    if dev_cfg == "auto":
        if av["cuda"]: d, c = "cuda", "float16"
        elif av["dml"]: d, c = "dml", "int8"
        else: d, c = "cpu", "int8"
    elif dev_cfg == "cuda": d, c = "cuda", "float16"
    elif dev_cfg == "dml":  d, c = "dml",  "int8"
    else:                   d, c = "cpu",  "int8"
    if compute_cfg != "auto": c = compute_cfg
    return d, c

# ─── Model loading ─────────────────────────────────────────────────────────────

def load_model(status_cb=None):
    global whisper_model
    if status_cb: status_cb("loading", f"Loading '{cfg['model']}'...")
    d, c = resolve_device(cfg["device"], cfg["compute_type"])
    lbl  = {"cuda": "CUDA (NVIDIA)", "dml": "NPU/DirectML", "cpu": "CPU"}.get(d, d)
    _log(f"ℹ️  Device: {lbl} | Compute: {c} | Model: {cfg['model']}")
    try:
        from faster_whisper import WhisperModel
        whisper_model = WhisperModel(cfg["model"], device=d, compute_type=c,
                                     download_root=MODEL_CACHE_DIR)
        if status_cb: status_cb("ready", f"{T('ready')}  [{lbl}]")
        _log(f"✅ Model loaded on {lbl}")
    except Exception as e:
        _log(f"⚠️  {lbl} failed: {e}")
        try:
            from faster_whisper import WhisperModel
            whisper_model = WhisperModel(cfg["model"], device="cpu", compute_type="int8",
                                         download_root=MODEL_CACHE_DIR)
            if status_cb: status_cb("ready", f"{T('ready')}  [CPU Fallback]")
            _log("✅ CPU fallback active")
        except Exception as e2:
            if status_cb: status_cb("error", T("load_error"))
            _log(f"❌ Error: {e2}")

def _log(msg):
    ui_queue.put(("log", msg))

# ─── Windows mic permission ────────────────────────────────────────────────────

def request_windows_mic_permission():
    _log("🔑 Requesting microphone permission...")
    try:
        import winrt.windows.media.capture as wmc
        import asyncio
        async def _req():
            cap = wmc.MediaCapture()
            s   = wmc.MediaCaptureInitializationSettings()
            s.stream_type = wmc.StreamingCaptureMode.AUDIO
            await cap.initialize_async(s)
            await cap.close_async()
        asyncio.run(_req())
        _log("✅ Mic permission granted via winrt.")
        return True
    except ImportError:
        pass
    except Exception as e:
        _log(f"⚠️  winrt failed: {e}")
    try:
        import winreg
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "Value", 0, winreg.REG_SZ, "Allow")
        _log("✅ Mic permission set via registry.")
        return True
    except Exception as e:
        _log(f"⚠️  Registry fix failed: {e}")
    try:
        subprocess.Popen(["ms-settings:privacy-microphone"],
                         shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        _log("ℹ️  Windows mic settings opened.")
        ui_queue.put(("mic_permission_dialog", None))
    except Exception:
        pass
    return False

def start_audio_stream():
    global _audio_stream, MIC_OK, _silent_count
    if _audio_stream is not None:
        try: _audio_stream.stop(); _audio_stream.close()
        except Exception: pass
        _audio_stream = None
    try:
        _audio_stream = sd.InputStream(
            samplerate=16000, channels=1, dtype="float32",
            callback=audio_callback, blocksize=512,
        )
        _audio_stream.start()
        _silent_count = 0; MIC_OK = True
        _log("✅ Audio stream started.")
        ui_queue.put(("mic_ok", None))
        return True
    except Exception as e:
        MIC_OK = False
        _log(f"❌ Audio stream error: {e}")
        ui_queue.put(("mic_error", str(e)))
        return False

def restart_audio_stream():
    _log("🔄 Restarting microphone...")
    request_windows_mic_permission()
    time.sleep(0.5)
    if start_audio_stream():
        ui_queue.put(("status", "ready", T("ready")))
    else:
        ui_queue.put(("status", "error", T("mic_error")))

# ─── Hotkey / PTT ──────────────────────────────────────────────────────────────

def parse_hotkey(hk_str: str) -> dict:
    parts   = [p.strip().lower() for p in hk_str.split("+")]
    mod_set = {"ctrl", "alt", "shift", "cmd"}
    mods, main, mouse = set(), None, None
    for p in parts:
        if p in mod_set:       mods.add(p)
        elif p.startswith("mouse_"): mouse = p
        else:                  main = p
    return {"mods": mods, "key": main, "mouse": mouse}

def _pynput_key_name(key) -> str:
    try:
        return key.char.lower()
    except AttributeError:
        name = str(key).replace("Key.", "").lower()
        for old, new in [("ctrl_l","ctrl"),("ctrl_r","ctrl"),
                         ("alt_l","alt"),("alt_r","alt"),("alt_gr","alt"),
                         ("shift_l","shift"),("shift_r","shift"),
                         ("cmd_l","cmd"),("cmd_r","cmd")]:
            name = name.replace(old, new)
        return name

def start_ptt_listener():
    global _ptt_kb_listener, _ptt_ms_listener
    stop_ptt_listener()
    hk        = parse_hotkey(cfg["hotkey"])
    mod_mods  = hk["mods"]
    hk_key    = hk["key"]
    hk_mouse  = hk["mouse"]
    held_keys = set()

    def mods_ok():
        return mod_mods.issubset(held_keys)

    def on_kb_press(key):
        kn = _pynput_key_name(key)
        held_keys.add(kn)
        if hk_key and kn == hk_key and mods_ok():
            _ptt_trigger_press()

    def on_kb_release(key):
        kn = _pynput_key_name(key)
        if hk_key and kn == hk_key:
            _ptt_trigger_release()
        held_keys.discard(kn)

    _ptt_kb_listener = pynput_kb.Listener(on_press=on_kb_press, on_release=on_kb_release, daemon=True)
    _ptt_kb_listener.start()

    if hk_mouse:
        target_btn = next((b for b, n in MOUSE_BTN_NAMES.items() if n == hk_mouse), None)
        def on_ms_press(x, y, button, pressed):
            if button == target_btn:
                if pressed and mods_ok(): _ptt_trigger_press()
                elif not pressed:         _ptt_trigger_release()
        _ptt_ms_listener = pynput_ms.Listener(on_click=on_ms_press, daemon=True)
        _ptt_ms_listener.start()

def stop_ptt_listener():
    global _ptt_kb_listener, _ptt_ms_listener
    for lst in (_ptt_kb_listener, _ptt_ms_listener):
        if lst:
            try: lst.stop()
            except Exception: pass
    _ptt_kb_listener = None; _ptt_ms_listener = None

def _ptt_trigger_press():
    global _ptt_active
    if not _ptt_active and whisper_model is not None:
        _ptt_active = True; start_recording()

def _ptt_trigger_release():
    global _ptt_active
    if _ptt_active:
        _ptt_active = False; stop_recording()
        threading.Thread(target=transcribe_and_paste, daemon=True).start()

# ─── Audio ─────────────────────────────────────────────────────────────────────

def audio_callback(indata, frames, time_info, status):
    global current_volume
    current_volume = min(float(np.sqrt(np.mean(indata ** 2))) * 8.0, 1.0)
    if status:
        ui_queue.put(("mic_stream_error", str(status)))
    if recording:
        audio_chunks.append(indata.copy())

def start_recording():
    global recording, audio_chunks
    with record_lock:
        audio_chunks = []; recording = True
    ui_queue.put(("status", "record", T("recording")))
    if cfg["sound_feedback"]: _beep(660, 0.08)

def stop_recording():
    global recording
    with record_lock:
        recording = False
    ui_queue.put(("status", "process", T("processing")))
    if cfg["sound_feedback"]: _beep(880, 0.10)

def _beep(freq=880, dur=0.08, vol=0.3):
    try:
        t    = np.linspace(0, dur, int(16000 * dur), False)
        wave = (np.sin(2 * np.pi * freq * t) * vol * 32767).astype(np.int16)
        sd.play(wave, 16000)
    except Exception:
        pass

# ─── Transcription ─────────────────────────────────────────────────────────────

def transcribe_and_paste():
    global _silent_count
    with record_lock:
        chunks = list(audio_chunks)
    if not chunks:
        ui_queue.put(("status", "ready", T("ready"))); return

    audio_data = np.concatenate(chunks, axis=0).flatten().astype(np.float32)

    if float(np.max(np.abs(audio_data))) < 0.001:
        _silent_count += 1
        _log(f"⚠️  {T('log_no_signal')} ({_silent_count}/{SILENT_THRESHOLD})")
        if _silent_count >= SILENT_THRESHOLD:
            _silent_count = 0
            _log(T("log_restarting"))
            ui_queue.put(("status", "error", T("mic_error")))
            threading.Thread(target=restart_audio_stream, daemon=True).start()
        ui_queue.put(("status", "ready", T("ready"))); return
    else:
        _silent_count = 0

    if len(audio_data) / 16000 < 0.3:
        ui_queue.put(("status", "ready", T("ready")))
        _log(T("log_too_short")); return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        sf.write(tmp_path, audio_data, 16000)

    try:
        t0 = time.time()
        in_lang  = cfg["language"] or None   # None = auto-detect
        out_lang = cfg.get("output_language", "same")
        # task="translate" makes Whisper translate output to English
        task = "translate" if (out_lang == "en" and in_lang != "en") else "transcribe"
        if task == "translate":
            _log("🌐 Translation mode: → English")
        seg, _ = whisper_model.transcribe(
            tmp_path,
            language=in_lang,
            task=task,
            beam_size=cfg["beam_size"],
            vad_filter=cfg["vad_filter"],
            vad_parameters=dict(min_silence_duration_ms=cfg["vad_silence_ms"]),
        )
        text    = " ".join(s.text.strip() for s in seg).strip()
        elapsed = time.time() - t0

        if not text:
            _log(T("log_no_text"))
            ui_queue.put(("status", "ready", T("ready"))); return

        ui_queue.put(("recognized", text))
        ui_queue.put(("status", "ready", f"{T('ready')}  ({elapsed:.1f}s)"))
        _do_paste(text)
    except Exception as e:
        _log(f"❌ Error: {e}")
        ui_queue.put(("status", "ready", T("ready")))
    finally:
        try: os.unlink(tmp_path)
        except Exception: pass

def _do_paste(text: str):
    time.sleep(0.15)
    if cfg["paste_mode"] == "clipboard":
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(text, interval=0.01)

# ─── UI helpers ────────────────────────────────────────────────────────────────

def _lighten(hex_c: str, f=1.3) -> str:
    h = hex_c.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return "#{:02x}{:02x}{:02x}".format(min(255,int(r*f)), min(255,int(g*f)), min(255,int(b*f)))

def _section(parent, key):
    text = T(key) if key in TRANSLATIONS else key
    if text:
        tk.Label(parent, text=text, bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(10,0))
    tk.Frame(parent, bg=C["sep"], height=1).pack(fill="x", pady=(2,4))

def _flat_btn(parent, key, color, cmd, padx=8, pady=4):
    text = T(key) if key in TRANSLATIONS else key
    f = tk.Frame(parent, bg=color, cursor="hand2")
    l = tk.Label(f, text=text, bg=color, fg=C["text"],
                 font=("Segoe UI", 8, "bold"), padx=padx, pady=pady, cursor="hand2")
    l.pack()
    def click(e): cmd()
    def enter(e): b=_lighten(color); f.config(bg=b); l.config(bg=b)
    def leave(e): f.config(bg=color); l.config(bg=color)
    for w in (f, l):
        w.bind("<Button-1>", click)
        w.bind("<Enter>", enter)
        w.bind("<Leave>", leave)
    return f

def _make_text_widget(parent, height=5):
    tf = tk.Frame(parent, bg=C["bg2"], highlightthickness=1,
                  highlightbackground=C["sep"])
    tf.pack(fill="both", expand=True, pady=(2,4))
    sb = tk.Scrollbar(tf, bg=C["bg"], troughcolor=C["bg2"],
                      relief="flat", bd=0, width=10)
    sb.pack(side="right", fill="y")
    txt = tk.Text(
        tf, height=height, width=36,
        bg=C["bg2"], fg=C["text"],
        insertbackground=C["text"],
        selectbackground=C["accent2"], selectforeground=C["text"],
        font=("Consolas", 9), wrap="word", relief="flat", bd=4,
        yscrollcommand=sb.set, cursor="xterm",
    )
    txt.pack(side="left", fill="both", expand=True)
    sb.config(command=txt.yview)
    txt.bind("<ButtonPress-1>",   lambda e: None)
    txt.bind("<B1-Motion>",       lambda e: None)
    txt.bind("<ButtonRelease-1>", lambda e: None)
    return txt

# ═══════════════════════════════════════════════════════════════════════════════
#  Main Overlay
# ═══════════════════════════════════════════════════════════════════════════════

class WhisperPTTApp:

    STATUS_COLORS = {
        "idle":    C["idle"],    "loading": C["process"],
        "ready":   C["ready"],   "record":  C["record"],
        "process": C["process"], "error":   C["record"],
    }

    def __init__(self, root: tk.Tk):
        self.root          = root
        self._minimized    = False
        self._settings_win = None
        self._clean_texts  = []

        self._build_window()
        self._build_ui()
        self._poll_queue()
        self._animate_meter()

        threading.Thread(
            target=load_model,
            args=(lambda s, m: ui_queue.put(("status", s, m)),),
            daemon=True,
        ).start()
        threading.Thread(target=start_ptt_listener, daemon=True).start()

    def _build_window(self):
        self.root.title("Whisper PTT")
        self.root.configure(bg=C["bg"])
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", cfg["opacity"])
        self.root.overrideredirect(True)
        self.root.resizable(False, False)
        self.root.update_idletasks()
        if cfg["window_x"] >= 0:
            self.root.geometry(f"+{cfg['window_x']}+{cfg['window_y']}")
        else:
            sw = self.root.winfo_screenwidth()
            self.root.geometry(f"+{sw - 370}+20")

    def _build_ui(self):
        outer = tk.Frame(self.root, bg=C["bg"],
                         highlightbackground=C["sep"], highlightthickness=1)
        outer.pack(fill="both", expand=True)

        # Title bar – drag only here
        self._bar = tk.Frame(outer, bg=C["accent"], height=30)
        self._bar.pack(fill="x")
        self._bar.bind("<ButtonPress-1>",   self._drag_start)
        self._bar.bind("<B1-Motion>",       self._drag_motion)
        self._bar.bind("<ButtonRelease-1>", self._drag_end)

        tk.Label(self._bar, text="🎤  Whisper PTT",
                 bg=C["accent"], fg=C["text"],
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=8, pady=5)

        for sym, cmd in [("✕", self._on_close), ("─", self._toggle_min)]:
            lb = tk.Label(self._bar, text=sym, bg=C["accent"], fg=C["dim"],
                          font=("Segoe UI", 11), cursor="hand2", padx=6)
            lb.pack(side="right")
            lb.bind("<Button-1>", lambda e, c=cmd: c())
            lb.bind("<Enter>",    lambda e, l=lb: l.config(fg=C["text"]))
            lb.bind("<Leave>",    lambda e, l=lb: l.config(fg=C["dim"]))

        # Content – no drag
        self.content = tk.Frame(outer, bg=C["bg"], padx=10, pady=8)
        self.content.pack(fill="both", expand=True)

        # Status row
        row = tk.Frame(self.content, bg=C["bg"])
        row.pack(fill="x", pady=(0, 5))

        self.dot_cv = tk.Canvas(row, width=14, height=14, bg=C["bg"],
                                highlightthickness=0)
        self.dot_cv.pack(side="left")
        self._dot = self.dot_cv.create_oval(2, 2, 12, 12, fill=C["idle"], outline="")

        self.status_lbl = tk.Label(row, text=T("initializing"),
                                   bg=C["bg"], fg=C["dim"],
                                   font=("Segoe UI", 9))
        self.status_lbl.pack(side="left", padx=(6, 0))

        gear = tk.Label(row, text="⚙", bg=C["bg"], fg=C["dim"],
                        font=("Segoe UI", 13), cursor="hand2")
        gear.pack(side="right")
        gear.bind("<Button-1>", lambda e: self._open_settings())
        gear.bind("<Enter>",    lambda e: gear.config(fg=C["text"]))
        gear.bind("<Leave>",    lambda e: gear.config(fg=C["dim"]))

        self.mic_btn = tk.Label(row, text="🎤↺", bg=C["bg"], fg=C["dim"],
                                font=("Segoe UI", 11), cursor="hand2")
        self.mic_btn.pack(side="right", padx=(0, 2))
        self.mic_btn.bind("<Button-1>", lambda e: self._retry_mic())
        self.mic_btn.bind("<Enter>",    lambda e: self.mic_btn.config(fg=C["process"]))
        self.mic_btn.bind("<Leave>",    lambda e: self.mic_btn.config(fg=C["dim"]))

        self.hotkey_lbl = tk.Label(row, text=cfg["hotkey"],
                                   bg=C["bg"], fg=C["dim"],
                                   font=("Segoe UI", 8))
        self.hotkey_lbl.pack(side="right", padx=(0, 4))

        # Voice meter
        tk.Label(self.content, text=T("microphone"), bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.meter_cv = tk.Canvas(self.content, height=16, bg=C["bg3"],
                                  highlightthickness=1, highlightbackground=C["sep"])
        self.meter_cv.pack(fill="x", pady=(2, 8))
        self._mbar = self.meter_cv.create_rectangle(0, 0, 0, 16,
                                                    fill=C["meter_low"], outline="")

        tk.Frame(self.content, bg=C["sep"], height=1).pack(fill="x", pady=(0, 6))

        # Panel 1: Recognized text
        tk.Label(self.content, text=T("recognized_text"), bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.recog_txt = _make_text_widget(self.content, height=5)

        br1 = tk.Frame(self.content, bg=C["bg"])
        br1.pack(fill="x", pady=(0, 6))
        _flat_btn(br1, "btn_copy",  C["btn_copy"],  self._copy_recog ).pack(side="left", padx=(0,4))
        _flat_btn(br1, "btn_paste", C["btn_paste"], self._paste_recog).pack(side="left", padx=(0,4))
        _flat_btn(br1, "btn_clear", C["btn_clear"], self._clear_recog).pack(side="right")

        tk.Frame(self.content, bg=C["sep"], height=1).pack(fill="x", pady=(0, 6))

        # Panel 2: Debug / Log
        tk.Label(self.content, text=T("debug_log"), bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 7, "bold")).pack(anchor="w")
        self.debug_txt = _make_text_widget(self.content, height=4)
        self.debug_txt.config(fg=C["dim"])

        br2 = tk.Frame(self.content, bg=C["bg"])
        br2.pack(fill="x", pady=(0, 0))
        _flat_btn(br2, "btn_clear_log", C["btn_clear"], self._clear_debug).pack(side="right")

    # ── Drag (title bar only) ──────────────────────────────────────────────────

    def _drag_start(self, e): self._dx = e.x; self._dy = e.y
    def _drag_motion(self, e):
        x = self.root.winfo_x() + (e.x - self._dx)
        y = self.root.winfo_y() + (e.y - self._dy)
        self.root.geometry(f"+{x}+{y}")
    def _drag_end(self, e):
        cfg["window_x"] = self.root.winfo_x()
        cfg["window_y"] = self.root.winfo_y()
        save_settings()

    # ── Actions ────────────────────────────────────────────────────────────────

    def _copy_recog(self):
        try:    text = self.recog_txt.get("sel.first", "sel.last")
        except: text = self._clean_texts[-1] if self._clean_texts else \
                        self.recog_txt.get("1.0", "end-1c").strip()
        if text:
            pyperclip.copy(text)
            self._flash(T("flash_copied"))

    def _paste_recog(self):
        text = self._clean_texts[-1] if self._clean_texts else \
               self.recog_txt.get("1.0", "end-1c").strip()
        if text:
            pyperclip.copy(text)
            self.root.after(150, lambda: pyautogui.hotkey("ctrl", "v"))
            self._flash(T("flash_pasted"))

    def _clear_recog(self):
        self._clean_texts.clear()
        self.recog_txt.config(state="normal")
        self.recog_txt.delete("1.0", "end")

    def _clear_debug(self):
        self.debug_txt.config(state="normal")
        self.debug_txt.delete("1.0", "end")

    def _flash(self, msg, ms=1500):
        old = self.status_lbl.cget("text")
        self.status_lbl.config(text=msg, fg=C["ready"])
        self.root.after(ms, lambda: self.status_lbl.config(text=old, fg=C["dim"]))

    def _retry_mic(self):
        self.mic_btn.config(fg=C["process"])
        self._set_status("process", T("mic_restart"))
        threading.Thread(target=restart_audio_stream, daemon=True).start()

    def _toggle_min(self):
        self._minimized = not self._minimized
        if self._minimized: self.content.pack_forget()
        else:               self.content.pack(fill="both", expand=True)

    def _on_close(self):
        cfg["window_x"] = self.root.winfo_x()
        cfg["window_y"] = self.root.winfo_y()
        save_settings()
        stop_ptt_listener()
        if _audio_stream is not None:
            try: _audio_stream.stop(); _audio_stream.close()
            except Exception: pass
        self.root.destroy()

    # ── Queue polling ──────────────────────────────────────────────────────────

    def _poll_queue(self):
        try:
            while True:
                msg = ui_queue.get_nowait()
                if msg[0] == "status":
                    self._set_status(msg[1], msg[2])
                elif msg[0] == "recognized":
                    self._append_recognized(msg[1])
                elif msg[0] == "log":
                    self._append_log(msg[1])
                elif msg[0] == "mic_ok":
                    self.mic_btn.config(fg=C["dim"])
                elif msg[0] in ("mic_error", "mic_stream_error"):
                    self.mic_btn.config(fg=C["record"])
                    self._append_log(f"🎤 Mic error: {msg[1]}")
                elif msg[0] == "mic_permission_dialog":
                    self._show_permission_hint()
        except queue.Empty:
            pass
        self.root.after(50, self._poll_queue)

    def _show_permission_hint(self):
        messagebox.showinfo(T("mic_perm_title"), T("mic_perm_msg"), parent=self.root)

    def _set_status(self, state, text):
        color = self.STATUS_COLORS.get(state, C["idle"])
        self.dot_cv.itemconfig(self._dot, fill=color)
        self.status_lbl.config(text=text,
                               fg=color if state not in ("ready","idle") else C["dim"])
        if state == "record": self._pulse(color)

    def _pulse(self, color, step=0):
        if not recording:
            self.dot_cv.itemconfig(self._dot, fill=color); return
        self.dot_cv.itemconfig(self._dot, fill=color if step%2==0 else C["bg2"])
        self.root.after(400, lambda: self._pulse(color, step+1))

    def _append_recognized(self, text: str):
        self._clean_texts.append(text)
        self.recog_txt.config(state="normal")
        if self.recog_txt.index("end-1c") != "1.0":
            self.recog_txt.insert("end", "\n─────\n")
        self.recog_txt.insert("end", text)
        self.recog_txt.see("end")

    def _append_log(self, text: str):
        self.debug_txt.config(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.debug_txt.insert("end", f"[{ts}] {text}\n")
        self.debug_txt.see("end")

    def _animate_meter(self):
        try:
            w  = self.meter_cv.winfo_width() or 300
            bw = int(w * current_volume)
            lv = current_volume
            c  = C["meter_low"] if lv < 0.5 else C["meter_mid"] if lv < 0.8 else C["meter_high"]
            self.meter_cv.coords(self._mbar, 0, 0, bw, 16)
            self.meter_cv.itemconfig(self._mbar, fill=c)
        except Exception: pass
        self.root.after(40, self._animate_meter)

    # ── Settings ───────────────────────────────────────────────────────────────

    def _open_settings(self):
        if self._settings_win is not None:
            try:
                if self._settings_win.win.winfo_exists():
                    self._settings_win.win.lift()
                    self._settings_win.win.focus_force()
                    return
            except Exception:
                pass
            self._settings_win = None
        self._settings_win = SettingsWindow(
            self.root,
            on_save_cb=self._on_settings_saved,
            on_close_cb=self._on_settings_closed,
        )

    def _on_settings_closed(self):
        self._settings_win = None

    def _on_settings_saved(self):
        self._settings_win = None
        self.hotkey_lbl.config(text=cfg["hotkey"])
        self.root.attributes("-alpha", cfg["opacity"])
        threading.Thread(target=start_ptt_listener, daemon=True).start()
        threading.Thread(
            target=load_model,
            args=(lambda s, m: ui_queue.put(("status", s, m)),),
            daemon=True,
        ).start()


# ═══════════════════════════════════════════════════════════════════════════════
#  Settings Window
# ═══════════════════════════════════════════════════════════════════════════════

class SettingsWindow:

    def __init__(self, parent, on_save_cb, on_close_cb):
        self.parent            = parent
        self.on_save_cb        = on_save_cb
        self.on_close_cb       = on_close_cb
        self._rec_kb_listener  = None
        self._rec_ms_listener  = None
        self._recording_hotkey = False
        self._held_kb          = set()
        self._held_ms          = set()

        self.win = tk.Toplevel(parent)
        self.win.title(T("settings_win_title"))
        self.win.configure(bg=C["bg"])
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        px, py = parent.winfo_x(), parent.winfo_y()
        self.win.geometry(f"460x700+{max(0, px-470)}+{py}")

        self._build()
        self._load_values()
        threading.Thread(target=self._detect_hw, daemon=True).start()

    def _on_close(self):
        self._stop_recorder()
        self.on_close_cb()
        self.win.destroy()

    # ── Notebook ───────────────────────────────────────────────────────────────

    def _build(self):
        main = tk.Frame(self.win, bg=C["bg"], padx=14, pady=10)
        main.pack(fill="both", expand=True)

        tk.Label(main, text=T("settings_title"),
                 bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0,8))

        style = ttk.Style(self.win)
        style.theme_use("clam")
        style.configure("TNotebook",     background=C["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=C["accent"], foreground=C["text"],
                        padding=(12,4), font=("Segoe UI", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", C["accent2"])],
                  foreground=[("selected", C["text"])])
        style.configure("TFrame", background=C["bg"])

        nb = ttk.Notebook(main)
        nb.pack(fill="both", expand=True, pady=(0,10))

        t1 = ttk.Frame(nb); nb.add(t1, text=T("tab_general"))
        t2 = ttk.Frame(nb); nb.add(t2, text=T("tab_audio"))
        t3 = ttk.Frame(nb); nb.add(t3, text=T("tab_advanced"))

        self._tab_general(t1)
        self._tab_audio(t2)
        self._tab_advanced(t3)

        bot = tk.Frame(main, bg=C["bg"])
        bot.pack(fill="x")

        self.hw_info_lbl = tk.Label(bot, text=T("checking_hw"),
                                    bg=C["bg"], fg=C["dim"],
                                    font=("Segoe UI", 7), wraplength=240)
        self.hw_info_lbl.pack(side="left")

        tk.Button(bot, text=T("btn_cancel"),
                  bg=C["btn_clear"], fg=C["text"], relief="flat",
                  activebackground=_lighten(C["btn_clear"]), activeforeground=C["text"],
                  cursor="hand2", padx=10, pady=5, font=("Segoe UI", 9),
                  command=self._on_close).pack(side="right", padx=(4,0))

        tk.Button(bot, text=T("btn_save"),
                  bg=C["btn_paste"], fg=C["text"], relief="flat",
                  activebackground=_lighten(C["btn_paste"]), activeforeground=C["text"],
                  cursor="hand2", padx=10, pady=5, font=("Segoe UI", 9, "bold"),
                  command=self._save).pack(side="right")

    # ── Tab 1: General ─────────────────────────────────────────────────────────

    def _tab_general(self, frame):
        p = tk.Frame(frame, bg=C["bg"], padx=14, pady=8)
        p.pack(fill="both", expand=True)

        # Hotkey recorder
        _section(p, "sec_hotkey")
        tk.Label(p, text=T("hotkey_hint"),
                 bg=C["bg"], fg=C["dim"], font=("Segoe UI", 8),
                 wraplength=390, justify="left").pack(anchor="w")

        hk_row = tk.Frame(p, bg=C["bg"])
        hk_row.pack(fill="x", pady=(6,0))

        self.hotkey_var = tk.StringVar(value=cfg["hotkey"])
        tk.Entry(hk_row, textvariable=self.hotkey_var,
                 bg=C["bg3"], fg=C["ready"],
                 font=("Consolas", 11, "bold"),
                 insertbackground=C["text"], relief="flat", bd=6,
                 width=20, state="readonly").pack(side="left")

        self.rec_btn = tk.Button(
            hk_row, text=T("btn_record"),
            bg=C["record"], fg=C["text"], relief="flat",
            activebackground=_lighten(C["record"]), activeforeground=C["text"],
            cursor="hand2", padx=8, pady=4, font=("Segoe UI", 8, "bold"),
            command=self._toggle_recorder,
        )
        self.rec_btn.pack(side="left", padx=6)

        tk.Button(hk_row, text="↺", bg=C["btn_set"], fg=C["dim"], relief="flat",
                  activebackground=_lighten(C["btn_set"]), activeforeground=C["text"],
                  cursor="hand2", padx=6, pady=4, font=("Segoe UI", 10),
                  command=lambda: self.hotkey_var.set(DEFAULTS["hotkey"])
                  ).pack(side="left")

        self.hk_hint = tk.Label(p, text="", bg=C["bg"], fg=C["process"],
                                font=("Segoe UI", 8))
        self.hk_hint.pack(anchor="w", pady=(4,0))

        # UI language
        _section(p, "sec_ui_lang")
        self.ui_lang_var = tk.StringVar()
        ttk.Combobox(p, textvariable=self.ui_lang_var,
                     values=list(UI_LANGUAGES.keys()), state="readonly", width=20,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,2))
        tk.Label(p, text=T("ui_lang_note"),
                 bg=C["bg"], fg=C["dim"], font=("Segoe UI", 8),
                 wraplength=390, justify="left").pack(anchor="w")

        # Recognition language (input)
        _section(p, "sec_rec_lang")
        self.lang_var = tk.StringVar()
        self._recog_labels = _recog_lang_labels(cfg["ui_lang"])
        ttk.Combobox(p, textvariable=self.lang_var,
                     values=list(self._recog_labels.values()), state="readonly", width=28,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,0))

        # Output language / translation
        _section(p, "sec_output_lang")
        self.out_lang_var = tk.StringVar()
        self._out_lang_options = {
            "same": T("output_same"),
            "en":   _recog_lang_labels(cfg["ui_lang"])["en"],
        }
        ttk.Combobox(p, textvariable=self.out_lang_var,
                     values=list(self._out_lang_options.values()), state="readonly", width=28,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,2))
        tk.Label(p, text=T("output_lang_note"),
                 bg=C["bg"], fg=C["dim"], font=("Segoe UI", 8),
                 wraplength=390, justify="left").pack(anchor="w")

        # Paste mode
        _section(p, "sec_paste")
        self.paste_var = tk.StringVar()
        for v, key in [("clipboard","paste_clipboard"), ("type","paste_type")]:
            tk.Radiobutton(p, text=T(key), variable=self.paste_var, value=v,
                           bg=C["bg"], fg=C["text"], selectcolor=C["bg3"],
                           activebackground=C["bg"], activeforeground=C["text"],
                           font=("Segoe UI", 9)).pack(anchor="w")

        # Appearance
        _section(p, "sec_appearance")
        self.sound_var = tk.BooleanVar()
        tk.Checkbutton(p, text=T("sound_feedback"), variable=self.sound_var,
                       bg=C["bg"], fg=C["text"], selectcolor=C["bg3"],
                       activebackground=C["bg"], activeforeground=C["text"],
                       font=("Segoe UI", 9)).pack(anchor="w")

        op_row = tk.Frame(p, bg=C["bg"])
        op_row.pack(fill="x", pady=(6,0))
        tk.Label(op_row, text=T("transparency"), bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 9)).pack(side="left")
        self.opacity_var = tk.DoubleVar()
        self.opacity_lbl = tk.Label(op_row, text="", bg=C["bg"], fg=C["dim"],
                                    font=("Segoe UI", 9), width=4)
        self.opacity_lbl.pack(side="right")
        tk.Scale(op_row, variable=self.opacity_var,
                 from_=0.4, to=1.0, resolution=0.05, orient="horizontal", length=180,
                 bg=C["bg"], fg=C["text"], troughcolor=C["bg3"],
                 highlightthickness=0, bd=0, showvalue=False,
                 command=lambda v: self.opacity_lbl.config(text=f"{float(v):.0%}")
                 ).pack(side="left", padx=6)

    # ── Tab 2: Audio / AI ──────────────────────────────────────────────────────

    def _tab_audio(self, frame):
        p = tk.Frame(frame, bg=C["bg"], padx=14, pady=8)
        p.pack(fill="both", expand=True)

        _section(p, "sec_device")
        self.device_var = tk.StringVar()
        # Build device labels in current UI lang
        dev_labels = list(DEVICES.values())
        ttk.Combobox(p, textvariable=self.device_var,
                     values=dev_labels, state="readonly", width=30,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,2))
        self.dev_lbl = tk.Label(p, text="", bg=C["bg"], fg=C["ready"],
                                font=("Segoe UI", 8), wraplength=390, justify="left")
        self.dev_lbl.pack(anchor="w", pady=(0,8))

        _section(p, "sec_compute")
        self.compute_var = tk.StringVar()
        ttk.Combobox(p, textvariable=self.compute_var,
                     values=list(COMPUTE_TYPES.values()), state="readonly", width=28,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4,2))
        tk.Label(p, text=T("compute_note"), bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 8)).pack(anchor="w")

        _section(p, "sec_model")
        model_desc_keys = {
            "tiny": "model_tiny", "base": "model_base", "small": "model_small",
            "medium": "model_medium", "large-v2": "model_large_v2", "large-v3": "model_large_v3",
        }
        self.model_var = tk.StringVar()
        for m in MODELS:
            row = tk.Frame(p, bg=C["bg"])
            row.pack(fill="x", pady=1)
            tk.Radiobutton(row, text=m, variable=self.model_var, value=m,
                           bg=C["bg"], fg=C["text"], selectcolor=C["bg3"],
                           activebackground=C["bg"], activeforeground=C["text"],
                           font=("Consolas", 9, "bold"), width=9, anchor="w").pack(side="left")
            tk.Label(row, text=T(model_desc_keys.get(m,"")), bg=C["bg"], fg=C["dim"],
                     font=("Segoe UI", 8)).pack(side="left")

    # ── Tab 3: Advanced ────────────────────────────────────────────────────────

    def _tab_advanced(self, frame):
        p = tk.Frame(frame, bg=C["bg"], padx=14, pady=8)
        p.pack(fill="both", expand=True)

        _section(p, "sec_vad")
        self.vad_var = tk.BooleanVar()
        tk.Checkbutton(p, text=T("vad_enable"), variable=self.vad_var,
                       bg=C["bg"], fg=C["text"], selectcolor=C["bg3"],
                       activebackground=C["bg"], activeforeground=C["text"],
                       font=("Segoe UI", 9)).pack(anchor="w", pady=(4,4))

        vad_row = tk.Frame(p, bg=C["bg"])
        vad_row.pack(anchor="w")
        tk.Label(vad_row, text=T("vad_threshold"), bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 9)).pack(side="left")
        self.vad_ms_var = tk.IntVar()
        tk.Spinbox(vad_row, textvariable=self.vad_ms_var,
                   from_=100, to=2000, increment=50, width=6,
                   bg=C["bg3"], fg=C["text"], buttonbackground=C["accent"],
                   insertbackground=C["text"], relief="flat",
                   font=("Segoe UI", 9)).pack(side="left", padx=6)
        tk.Label(vad_row, text="ms", bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 9)).pack(side="left")

        _section(p, "sec_beam")
        beam_row = tk.Frame(p, bg=C["bg"])
        beam_row.pack(anchor="w", pady=(4,0))
        tk.Label(beam_row, text="Beam Size:", bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 9)).pack(side="left")
        self.beam_var = tk.IntVar()
        tk.Spinbox(beam_row, textvariable=self.beam_var,
                   from_=1, to=10, increment=1, width=4,
                   bg=C["bg3"], fg=C["text"], buttonbackground=C["accent"],
                   insertbackground=C["text"], relief="flat",
                   font=("Segoe UI", 9)).pack(side="left", padx=6)
        tk.Label(beam_row, text=T("beam_hint"), bg=C["bg"], fg=C["dim"],
                 font=("Segoe UI", 8)).pack(side="left")

        _section(p, "")
        tk.Button(p, text=T("btn_reset"),
                  bg=C["btn_clear"], fg=C["dim"], relief="flat",
                  activebackground=_lighten(C["btn_clear"]), activeforeground=C["text"],
                  cursor="hand2", padx=8, pady=4, font=("Segoe UI", 8),
                  command=self._reset).pack(anchor="w", pady=(10,0))

    # ── Load values ────────────────────────────────────────────────────────────

    def _load_values(self):
        self.hotkey_var.set(cfg["hotkey"])
        self.paste_var.set(cfg["paste_mode"])
        self.sound_var.set(cfg["sound_feedback"])
        self.opacity_var.set(cfg["opacity"])
        self.opacity_lbl.config(text=f"{cfg['opacity']:.0%}")
        self.model_var.set(cfg["model"])
        self.vad_var.set(cfg["vad_filter"])
        self.vad_ms_var.set(cfg["vad_silence_ms"])
        self.beam_var.set(cfg["beam_size"])

        # UI language
        ui_lbl = next((k for k,v in UI_LANGUAGES.items() if v==cfg.get("ui_lang","en")), "English")
        self.ui_lang_var.set(ui_lbl)

        # Recognition language (input)
        rl = _recog_lang_labels(cfg["ui_lang"])
        rec_code = cfg.get("language") or "auto"
        self.lang_var.set(rl.get(rec_code, rl["auto"]))

        # Output language
        out_opts = {"same": T("output_same"), "en": rl["en"]}
        out_code = cfg.get("output_language", "same")
        self.out_lang_var.set(out_opts.get(out_code, out_opts["same"]))

        # Device
        self.device_var.set(DEVICES.get(cfg["device"], "Auto"))

        # Compute type
        self.compute_var.set(COMPUTE_TYPES.get(cfg["compute_type"], "Auto"))

    def _detect_hw(self):
        devs  = detect_devices()
        na    = T("hw_not_available")
        av    = T("hw_available")
        parts = [
            f"{'✅' if devs['cuda'] else '❌'} CUDA: {devs['cuda_name'] or na}",
            f"{'✅' if devs['dml']  else '❌'} NPU/DirectML: {devs.get('npu_name','') or (av if devs['dml'] else na)}",
        ]
        text = "   |   ".join(parts)
        try:
            self.dev_lbl.config(text=text)
            self.hw_info_lbl.config(text=text)
        except Exception:
            pass

    # ── Hotkey recorder ────────────────────────────────────────────────────────

    def _toggle_recorder(self):
        if self._recording_hotkey: self._stop_recorder()
        else:                      self._start_recorder()

    def _start_recorder(self):
        self._recording_hotkey = True
        self._held_kb.clear(); self._held_ms.clear()
        self.rec_btn.config(text=T("btn_stop_record"), bg=C["process"])
        self.hotkey_var.set(T("recorder_prompt"))
        self.hk_hint.config(text=T("recorder_hint"))

        def on_kb_press(key):
            if not self._recording_hotkey: return
            kn = self._key_name(key)
            self._held_kb.add(kn)
            try: self.hotkey_var.set(self._build_combo())
            except Exception: pass

        def on_kb_release(key):
            if not self._recording_hotkey: return
            kn = self._key_name(key)
            combo = self._build_combo()
            if any(k not in {"ctrl","alt","shift","cmd","windows"}
                   for k in (self._held_kb | self._held_ms)):
                try: self.hotkey_var.set(combo)
                except Exception: pass
                self.win.after(0, self._stop_recorder)
            self._held_kb.discard(kn)

        def on_ms_click(x, y, button, pressed):
            if not self._recording_hotkey: return
            btn_name = MOUSE_BTN_NAMES.get(button, f"mouse_{button}")
            if pressed:
                self._held_ms.add(btn_name)
                try: self.hotkey_var.set(self._build_combo())
                except Exception: pass
            else:
                combo = self._build_combo()
                try: self.hotkey_var.set(combo)
                except Exception: pass
                self._held_ms.discard(btn_name)
                self.win.after(0, self._stop_recorder)

        self._rec_kb_listener = pynput_kb.Listener(
            on_press=on_kb_press, on_release=on_kb_release, daemon=True)
        self._rec_ms_listener = pynput_ms.Listener(on_click=on_ms_click, daemon=True)
        self._rec_kb_listener.start()
        self._rec_ms_listener.start()

    def _stop_recorder(self):
        self._recording_hotkey = False
        for lst in (self._rec_kb_listener, self._rec_ms_listener):
            if lst:
                try: lst.stop()
                except Exception: pass
        self._rec_kb_listener = None; self._rec_ms_listener = None
        try:
            self.rec_btn.config(text=T("btn_record"), bg=C["record"])
            self.hk_hint.config(text="")
        except Exception: pass

    @staticmethod
    def _key_name(key) -> str:
        try: return key.char.lower()
        except AttributeError:
            name = str(key).replace("Key.", "").lower()
            for old, new in [("ctrl_l","ctrl"),("ctrl_r","ctrl"),
                             ("alt_l","alt"),("alt_r","alt"),("alt_gr","alt"),
                             ("shift_l","shift"),("shift_r","shift"),
                             ("cmd_l","cmd"),("cmd_r","cmd")]:
                name = name.replace(old, new)
            return name

    def _build_combo(self) -> str:
        priority = ["ctrl","alt","shift","cmd","windows"]
        kb_mods  = [k for k in priority if k in self._held_kb]
        kb_other = [k for k in self._held_kb if k not in priority]
        ms_keys  = sorted(self._held_ms)
        return "+".join(kb_mods + kb_other + ms_keys)

    # ── Save ───────────────────────────────────────────────────────────────────

    def _save(self):
        self._stop_recorder()
        hk = self.hotkey_var.get()
        if "▶" in hk or not hk: hk = DEFAULTS["hotkey"]
        cfg["hotkey"]         = hk
        cfg["ui_lang"]        = UI_LANGUAGES.get(self.ui_lang_var.get(), "en")

        # Resolve recognition language (label → code)
        rl      = _recog_lang_labels(cfg["ui_lang"])
        sel_lbl = self.lang_var.get()
        cfg["language"] = next((code for code, lbl in rl.items() if lbl == sel_lbl), None)

        # Resolve output language (label → code)
        out_opts = {"same": T("output_same"), "en": rl["en"]}
        sel_out  = self.out_lang_var.get()
        cfg["output_language"] = next((code for code, lbl in out_opts.items() if lbl == sel_out), "same")

        cfg["paste_mode"]     = self.paste_var.get()
        cfg["sound_feedback"] = self.sound_var.get()
        cfg["opacity"]        = round(self.opacity_var.get(), 2)
        cfg["model"]          = self.model_var.get()
        cfg["device"]         = next((k for k,v in DEVICES.items() if v==self.device_var.get()), "auto")
        cfg["compute_type"]   = next((k for k,v in COMPUTE_TYPES.items() if v==self.compute_var.get()), "auto")
        cfg["vad_filter"]     = self.vad_var.get()
        cfg["vad_silence_ms"] = self.vad_ms_var.get()
        cfg["beam_size"]      = self.beam_var.get()
        save_settings()
        self.on_save_cb()
        self.win.destroy()

    def _reset(self):
        if messagebox.askyesno(T("reset_confirm_title"), T("reset_confirm_msg"),
                               parent=self.win):
            cfg.update(DEFAULTS)
            self._load_values()

# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    load_settings()

    root = tk.Tk()
    app  = WhisperPTTApp(root)

    threading.Thread(target=start_audio_stream, daemon=True).start()

    root.mainloop()

    if _audio_stream is not None:
        try: _audio_stream.stop(); _audio_stream.close()
        except Exception: pass

if __name__ == "__main__":
    main()
