@echo off
rem The head pipeline on Windows (ours): headwrap.bat status | texture | build | game [--model hero1] | all
rem Without arguments it asks for the step. W = the folder with corsairs-remake and lama (set it if it is not the parent folder).
rem build also prints the eye score table (eye_score.py); the window stays open at the end.
cd /d "%~dp0"
set ARGS=%*
if "%ARGS%"=="" (
  echo Steps: status, texture, build, game, all
  set /p ARGS=Step [+ options, e.g. game --model hero1]: 
)
python headwrap.py %ARGS%
set RC=%ERRORLEVEL%
pause
exit /b %RC%
