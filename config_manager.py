import os
import sys
import json

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def save_config(model, base_url, api_key, prompts_dict, current_prompt_name, chunk_size=10000, chunk_overlap=1500, max_workers=1, output_format="spr"):
    """Сохраняет настройки и библиотеку промптов в JSON файл"""
    config_data = {
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "max_workers": max_workers,
        "output_format": output_format,
        "prompts": prompts_dict,
        "current_prompt_name": current_prompt_name
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

def load_config():
    """Загружает настройки из JSON файла"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None