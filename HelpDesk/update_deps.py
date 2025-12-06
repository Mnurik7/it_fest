#!/usr/bin/env python
"""Скрипт для обновления зависимостей для Python 3.14"""
import subprocess
import sys

packages = [
    "protobuf>=6.0.0",
    "google-generativeai>=0.8.0"
]

print("Обновление зависимостей для совместимости с Python 3.14...")
for package in packages:
    print(f"Установка {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package])

print("\nЗависимости обновлены! Теперь можно запустить app.py")

