"""
ptt/constants.py – All compile-time constants (no runtime logic, no local imports).
"""

VERSION = "0.8.1"

import sys
from pathlib import Path
from pynput import mouse as pynput_ms

# ─── Paths ──────────────────────────────────────────────────────────────────────

BASE_DIR        = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent
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
    "models_dir":      "",   # empty = BASE_DIR/models
    "mic_device":      -1,   # -1 = default device, else device index
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
    "sec_mic_device": {
        "en": "Microphone Device",
        "de": "Mikrofon-Gerät",
        "fr": "Périphérique micro",
        "es": "Dispositivo micrófono",
    },
    "mic_device_hint": {
        "en": "Select which microphone to use. 'Default' uses system default.",
        "de": "Wähle welches Mikrofon verwendet wird. 'Default' nutzt das System-Standard.",
        "fr": "Sélectionner le micro à utiliser. 'Default' utilise celui par défaut.",
        "es": "Seleccionar qué micrófono usar. 'Default' usa el predeterminado del sistema.",
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
    # ── Model cache directory ──────────────────────────────────────────────────
    "sec_models_dir": {
        "en": "Model Cache Directory",
        "de": "Modell-Cache-Verzeichnis",
        "fr": "Répertoire cache des modèles",
        "es": "Directorio caché de modelos",
    },
    "models_dir_hint": {
        "en": "Leave empty to use default (next to the .exe)",
        "de": "Leer lassen für Standard (neben der .exe)",
        "fr": "Laisser vide pour utiliser le défaut (à côté du .exe)",
        "es": "Dejar vacío para usar el predeterminado (junto al .exe)",
    },
    "btn_browse": {
        "en": "Browse…", "de": "Auswählen…",
        "fr": "Parcourir…", "es": "Examinar…",
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

MODELS     = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
MODELS_OV  = {
    "tiny":     "OpenVINO/whisper-tiny-fp16-ov",
    "base":     "OpenVINO/whisper-base-fp16-ov",
    "small":    "OpenVINO/whisper-small-fp16-ov",
    "medium":   "OpenVINO/whisper-medium-fp16-ov",
    "large-v2": "OpenVINO/whisper-large-v2-fp16-ov",
    "large-v3": "OpenVINO/whisper-large-v3-int8-ov",
}
DEVICES      = {"auto": "Auto", "cuda": "NVIDIA CUDA", "npu": "NPU (OpenVINO)", "cpu": "CPU"}
COMPUTE_TYPES = {"auto": "Auto", "float16": "float16 (GPU)", "int8": "int8", "float32": "float32 (CPU)"}

MOUSE_BTN_NAMES = {
    pynput_ms.Button.left:   "mouse_left",
    pynput_ms.Button.right:  "mouse_right",
    pynput_ms.Button.middle: "mouse_middle",
    pynput_ms.Button.x1:     "mouse_x1",
    pynput_ms.Button.x2:     "mouse_x2",
}

SILENT_THRESHOLD = 3
