@echo off
title BKK HEV Car 1311 Tracker

if "%BKK_API_KEY%"=="" (
    echo No BKK_API_KEY found in environment.
    echo.
    echo Get a free key at: https://opendata.bkk.hu/keys
    echo.
    set /p BKK_API_KEY=Paste your API key here and press Enter:
    echo.
)

py tracker.py
pause
