import os
import json

CONFIG_FILE = "config.json"

def save_config(model, base_url, api_key, prompts_dict, current_prompt_name):
    """Сохраняет настройки и библиотеку промптов в JSON файл"""
    config_data = {
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
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