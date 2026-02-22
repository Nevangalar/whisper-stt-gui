@echo off
REM ================================================
REM  Whisper PTT GUI v3 – Setup + .exe Build
REM ================================================
setlocal
echo.
echo  ================================================
echo   Whisper PTT GUI v3 – Setup und .exe Build
echo  ================================================

echo.
echo [1/5] Virtuelle Umgebung...
if not exist venv ( python -m venv venv )
call venv\Scripts\activate

echo.
echo [2/5] CUDA PyTorch (cu121)...
pip install torch --index-url https://download.pytorch.org/whl/cu121 --quiet

echo.
echo [3/5] Abhaengigkeiten...
REM pynput ersetzt keyboard-Lib (unterstuetzt Keyboard + Maustasten)
REM winrt fuer Windows Mikrofon-Berechtigungsanfrage
pip install faster-whisper sounddevice soundfile numpy pynput pyperclip pyautogui pyinstaller --quiet
pip install winrt-Windows.Media.Capture --quiet 2>nul || echo        (winrt optional - kein Fehler)

echo.
echo [4/5] CUDA-Check...
python -c "import torch; g=torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Keine GPU'; print(f'  GPU: {g}')"

echo.
echo [5/5] .exe bauen (1-3 Minuten)...
pyinstaller whisper_ptt_gui.spec --noconfirm --clean

echo.
if exist "dist\WhisperPTT\WhisperPTT.exe" (
    echo  ================================================
    echo   BUILD ERFOLGREICH!
    echo   EXE: dist\WhisperPTT\WhisperPTT.exe
    echo.
    echo   Den ganzen Ordner dist\WhisperPTT\ kopieren!
    echo   settings.json wird neben der .exe gespeichert.
    echo  ================================================
) else (
    echo  FEHLER: .exe nicht erstellt - siehe Log oben.
)
echo.
pause
