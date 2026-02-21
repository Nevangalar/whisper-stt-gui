@echo off
REM Whisper PTT - GPU Setup (faster-whisper + CUDA)
REM =================================================
echo.
echo [1/4] Erstelle virtuelle Umgebung...
python -m venv venv
call venv\Scripts\activate

echo.
echo [2/4] Installiere CUDA PyTorch...
pip install torch --index-url https://download.pytorch.org/whl/cu121

echo.
echo [3/4] Installiere faster-whisper + Abhaengigkeiten...
pip install faster-whisper sounddevice soundfile numpy keyboard pyperclip pyautogui

echo.
echo [4/4] Pruefe CUDA-Verfuegbarkeit...
python -c "import torch; print('CUDA verfuegbar:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Keine')"

echo.
echo ============================================
echo  Setup abgeschlossen!
echo  Beim ersten Start wird das Whisper-Modell
echo  (~150MB) automatisch heruntergeladen.
echo ============================================
echo.
pause
python whisper_ptt_gpu.py
