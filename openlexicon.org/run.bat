call "venv\Scripts\activate"

:: Start REDIS
START "redisprompt" redis/redis-server.exe
timeout /t 2

:: Start Server
start "serverprompt" cmd.exe /c "python3 manage.py runserver"
timeout /t 2

:loop
set /p answer= Type q to kill:
:: accepts only one character
if /i "%answer:~,1%" EQU "q" goto exit
goto loop

:: For kill to work, we need to run console in administrator mode
:: Kill all on quit. Use /F to force.
:exit
taskkill /F /FI "WINDOWTITLE eq serverprompt" /T
taskkill /F /FI "WINDOWTITLE eq redisprompt" /T
