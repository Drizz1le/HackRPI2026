@echo off
REM HackRPI 2026 vuln-hunting swarm.
REM   start.bat -master       coordinator + synthesizer + a local worker
REM   start.bat <master-ip>   a worker, on every other machine
REM
REM Each machine runs its own local Qwen server (llama-server), started below.
REM Set MODEL_MODE=stub to wire up and test the LAN with no model loaded.
setlocal
cd /d "%~dp0"

if /i "%~1"=="" goto usage

REM ---- local Qwen server: tuned flags carried over from the old launcher ----
set "LLAMA=C:\Users\Ben\llama.cpp\build-cuda\bin"
set "BLOB=C:\Users\Ben\.ollama\models\blobs\sha256-17409d9bf3128e9d6b67404da70079d97b158047379dcb6560657759e04f34b5"
set "TEMPLATE=C:\Users\Ben\llama.cpp\qwen36-template.jinja"

if /i "%MODEL_MODE%"=="stub" goto deps

curl.exe -s -o nul http://127.0.0.1:8080/health && goto wait
start "qwen-server" /d "%LLAMA%" "%LLAMA%\llama-server.exe" -m "%BLOB%" -ngl 99 -ncmoe 32 -lm none --parallel 1 -c 262144 -ctk q8_0 -ctv q8_0 -fa on --jinja --chat-template-file "%TEMPLATE%" --chat-template-kwargs "{\"enable_thinking\":false}" --host 127.0.0.1 --port 8080

echo waiting for Qwen on :8080 ...
set /a _t=0
:wait
curl.exe --fail -s -o nul http://127.0.0.1:8080/health && goto deps
set /a _t+=1
if %_t% geq 90 ( echo Qwen not ready after ~180s; check the qwen-server window & exit /b 1 )
timeout /t 2 /nobreak >nul
goto wait

:deps
python -m pip install -q -r requirements.txt

if /i "%~1"=="-master" goto master

REM ---- worker mode ----
set "SERVER=http://%~1:8765"
echo worker -^> %SERVER%
python src\worker.py
exit /b %errorlevel%

:master
for /f %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*' } ^| Select-Object -First 1).IPAddress"') do set "MYIP=%%i"
echo ==================================================
echo   Master IP: %MYIP%
echo   On every other machine run:  start.bat %MYIP%
echo ==================================================
python src\master.py
exit /b %errorlevel%

:usage
echo Usage:
echo   start.bat -master         ^(coordinator machine^)
echo   start.bat ^<master-ip^>     ^(every other machine^)
exit /b 1
