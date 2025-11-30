@echo off
title CMMS Stopper
powershell -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
