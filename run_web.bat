@echo off
title BKK HEV 1311 Web Tracker

if "%BKK_API_KEY%"=="" (
    set /p BKK_API_KEY=Paste your BKK API key:
    echo.
)

start "" "http://localhost:5000"
py app.py
pause
