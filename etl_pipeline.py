import os
import shutil
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
import frontmatter

try:
    import docx
except ImportError:
    docx = None

def extract_text_from_file(file_path, log_callback=None):
    """Извлекает текст из TXT, MD или DOCX файлов"""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in [".docx", ".doc"]:
        if docx is None:
            raise ImportError("Библиотека python-docx не установлена! Выполните: pip install python-docx")
        
        if log_callback:
            log_callback("Чтение документа Word...")
            
        try:
            doc = docx.Document(file_path)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as doc_err:
            raise Exception(f"Не удалось прочитать Word файл. Если это старый формат .doc, пересохраните его в .docx! Ошибка: {doc_err}")
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

def process_pipeline(cfg, progress_callback, log_callback, stop_check_callback):
    """
    Главный конвейер обработки данных.
    progress_callback: функция вида fn(chunk_val, total_val)
    log_callback: функция вида fn(message_text)
    stop_check_callback: функция вида fn() -> bool (проверка нажатия Стоп)
    """
    # === ЭТАП 1: Нарезка файла ===
    log_callback("--- ЭТАП 1: Нарезка файла ---")
    if not os.path.exists(cfg["raw_dir"]):
        os.makedirs(cfg["raw_dir"])
        
    text = extract_text_from_file(cfg["src_file"], log_callback)
    
    if not text.strip():
        raise Exception("Файл пуст или не содержит читаемого текста!")
        
    splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1500, length_function=len)
    chunks = splitter.split_text(text)
    total_chunks = len(chunks)
    log_callback(f"Текст успешно извлечен и нарезан на {total_chunks} кусков.")
    
    for i, chunk_data in enumerate(chunks):
        chunk_file = os.path.join(cfg["raw_dir"], f"{cfg['base_name']}_{i:03d}.txt")
        with open(chunk_file, 'w', encoding='utf-8') as f_out:
            f_out.write(chunk_data)
            
    # === ЭТАП 2: Анализ SPR через LLM ===
    log_callback("--- ЭТАП 2: Анализ SPR через LLM ---")
    if not os.path.exists(cfg["processed_dir"]):
        os.makedirs(cfg["processed_dir"])
        
    client = OpenAI(base_url=cfg["url"], api_key=cfg["key"])
    raw_files = sorted([f for f in os.listdir(cfg["raw_dir"]) if f.startswith(cfg["base_name"])])
    
    for idx, file_name in enumerate(raw_files):
        if stop_check_callback():
            log_callback("⚠️ Конвейер остановлен пользователем.")
            return False
        
        total_percent = int((idx / total_chunks) * 100)
        progress_callback(30, total_percent) 
        
        raw_path = os.path.join(cfg["raw_dir"], file_name)
        processed_path = os.path.join(cfg["processed_dir"], file_name)
        
        if os.path.exists(processed_path):
            log_callback(f"[{idx+1}/{total_chunks}] {file_name} уже обработан.")
            next_percent = int(((idx + 1) / total_chunks) * 100)
            progress_callback(100, next_percent)
            continue
            
        with open(raw_path, 'r', encoding='utf-8') as f:
            chunk_text = f.read()
            
        log_callback(f"[{idx+1}/{total_chunks}] Запрос к LLM ({cfg['model']})...")
        
        try:
            response = client.chat.completions.create(
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": cfg["prompt"]},
                    {"role": "user", "content": f"Вот текст для обработки:\n\n{chunk_text}"}
                ],
                temperature=0.2
            )
            llm_output = response.choices[0].message.content
            
            with open(processed_path, 'w', encoding='utf-8') as f_out:
                f_out.write(llm_output)
                
            next_percent = int(((idx + 1) / total_chunks) * 100)
            progress_callback(100, next_percent)
            
        except Exception as ex:
            raise Exception(f"Ошибка LLM на чанке {file_name}: {ex}")
            
    # === ЭТАП 3: Упаковка в итоговые .md файлы ===
    log_callback("--- ЭТАП 3: Упаковка в итоговые .md файлы ---")
    if not os.path.exists(cfg["final_dir"]):
        os.makedirs(cfg["final_dir"])
        
    processed_files = sorted([f for f in os.listdir(cfg["processed_dir"]) if f.startswith(cfg["base_name"])])
    
    for file_name in processed_files:
        proc_path = os.path.join(cfg["processed_dir"], file_name)
        
        with open(proc_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
            
        try:
            parsed = frontmatter.loads(raw_content)
            metadata = parsed.metadata
            content = parsed.content
        except Exception:
            log_callback(f"⚠️ Ошибка YAML в файле {file_name}. Применяем резервный парсер...")
            metadata = {}
            content = raw_content
            for line in raw_content.split('\n'):
                if line.startswith('title:') or line.startswith('- title:'):
                    metadata['title'] = line.split(':', 1)[1].strip().strip('"\'')
                elif line.startswith('концепция:') or line.startswith('- концепция:'):
                    metadata['концепция'] = line.split(':', 1)[1].strip().strip('"\'')

        title = metadata.get("title", f"Документ {os.path.splitext(file_name)[0]}")
        koncept = metadata.get("концепция", "Не указана (ошибка парсинга YAML)")
        algo = metadata.get("алгоритм", "Отсутствует")
        formula = metadata.get("формула", "Не применимо")
        metafora = metadata.get("метафора", "Отсутствует")
        svyazi = metadata.get("связи", "Нет связей")
        
        tags_list = metadata.get("теги", metadata.get("tags", []))
        formatted_tags = ", ".join([f"#{t.strip()}" for t in tags_list]) if isinstance(tags_list, list) else str(tags_list)
        
        new_content = (
            f"# {title}\n\n"
            f"## 🧠 Краткое представление (SPR)\n"
            f"* **Концепция:** {koncept}\n"
            f"* **Алгоритм:** {algo}\n"
            f"* **Формула:** {formula}\n"
            f"* **Метафора:** {metafora}\n"
            f"* **Связи:** {svyazi}\n"
            f"* **Теги:** {formatted_tags}\n\n"
            f"---\n\n"
            f"## 📄 Полный текст фрагмента\n"
            f"{content}"
        )
        
        clean_title = "".join([c if c.isalnum() or c in " _-" else "" for c in title]).strip().replace(" ", "_")
        
        max_len = 40
        if len(clean_title) > max_len:
            truncated = clean_title[:max_len]
            clean_title = truncated.rsplit("_", 1)[0] if "_" in truncated else truncated
            
        file_idx = processed_files.index(file_name) + 1
        final_filename = f"{file_idx:02d}_{clean_title}.md"
        
        with open(os.path.join(cfg["final_dir"], final_filename), 'w', encoding='utf-8') as f_out:
            f_out.write(new_content)
        
        # === ФИНАЛЬНАЯ ОЧИСТКА ===
    if cfg.get("cleanup", True):
        log_callback("🧹 Очистка временных файлов (raw и processed)...")
        try:
            if os.path.exists(cfg["raw_dir"]):
                shutil.rmtree(cfg["raw_dir"])
            if os.path.exists(cfg["processed_dir"]):
                shutil.rmtree(cfg["processed_dir"])
            log_callback("✅ Временные папки удалены.")
        except Exception as e:
            log_callback(f"⚠️ Ошибка при очистке: {e}")
    else:
        log_callback("ℹ️ Очистка пропущена (флаг снят).")

    return True