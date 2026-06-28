import os
import shutil
import frontmatter
import threading
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import docx
except ImportError:
    docx = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pytesseract
    from PIL import Image
    import io
    pytesseract.get_tesseract_version()
    OCR_AVAILABLE = True
except Exception:
    pytesseract = None
    Image = None
    OCR_AVAILABLE = False

def _ocr_pdf_page(page):
    """Распознаёт текст на странице PDF через Tesseract OCR."""
    pix = page.get_pixmap(dpi=150)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img, lang="rus+eng")
    return text.strip()

def extract_text_from_file(file_path, log_callback=None):
    """Извлекает текст из TXT, MD, DOCX или PDF файлов"""
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
    elif ext == ".pdf":
        if fitz is None:
            raise ImportError("Библиотека PyMuPDF не установлена! Выполните: pip install PyMuPDF")
        
        if log_callback:
            log_callback("Чтение PDF документа...")
        
        try:
            doc = fitz.open(file_path)
            pages_text = []
            ocr_used = False
            
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    pages_text.append(text)
                elif OCR_AVAILABLE:
                    if log_callback:
                        log_callback(f"  Страница {page_num + 1}: текст не найден, распознавание через OCR...")
                    ocr_text = _ocr_pdf_page(page)
                    if ocr_text:
                        pages_text.append(ocr_text)
                        ocr_used = True
                    else:
                        if log_callback:
                            log_callback(f"  ⚠️ Страница {page_num + 1}: OCR не вернул текст")
                else:
                    if log_callback:
                        log_callback(f"  ⚠️ Страница {page_num + 1}: текст не найден (установите Tesseract-OCR для распознавания сканов)")
            
            doc.close()
            
            if ocr_used and log_callback:
                log_callback("✅ OCR-распознавание завершено.")
            
            return "\n".join(pages_text)
        except Exception as pdf_err:
            raise Exception(f"Не удалось прочитать PDF файл: {pdf_err}")
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

def process_pipeline(cfg, progress_callback, log_callback, stop_check_callback, current_file_idx, total_files):
    """
    Главный конвейер обработки данных.
    progress_callback: функция вида fn(chunk_val, total_val)
    log_callback: функция вида fn(message_text)
    stop_check_callback: функция вида fn() -> bool (проверка нажатия Стоп)
    Добавил параметры current_file_idx и total_files для точного расчета прогресса.
    """
    # === ЭТАП 1: Нарезка файла ===
    log_callback("--- ЭТАП 1: Нарезка файла ---")
    if not os.path.exists(cfg["raw_dir"]):
        os.makedirs(cfg["raw_dir"])
        
    text = extract_text_from_file(cfg["src_file"], log_callback)
    if not text.strip():
        raise Exception("Файл пуст или не содержит читаемого текста!")
    
    c_size = cfg.get("chunk_size", 10000)
    c_overlap = cfg.get("chunk_overlap", 1500)
        
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=c_size, 
        chunk_overlap=c_overlap, 
        length_function=len
    )
    chunks = splitter.split_text(text)
    total_chunks = len(chunks)
    log_callback(f"Текст нарезан на {total_chunks} кусков.")
    
    for i, chunk_data in enumerate(chunks):
        chunk_file = os.path.join(cfg["raw_dir"], f"{cfg['base_name']}_{i:03d}.txt")
        with open(chunk_file, 'w', encoding='utf-8') as f_out:
            f_out.write(chunk_data)
            
    # === ЭТАП 2: Анализ SPR через LLM ===
    skip_llm = cfg.get("skip_llm", False)
    if skip_llm:
        log_callback("--- ЭТАП 2: пропущен (режим только нарезки) ---")
    else:
        log_callback("--- ЭТАП 2: Анализ SPR через LLM ---")
    if not os.path.exists(cfg["processed_dir"]):
        os.makedirs(cfg["processed_dir"])
        
    if not skip_llm:
        client = OpenAI(base_url=cfg["url"], api_key=cfg["key"])
    raw_files = sorted([f for f in os.listdir(cfg["raw_dir"]) if f.startswith(cfg["base_name"])])
    
    for idx, file_name in enumerate(raw_files):
        if stop_check_callback():
            log_callback("⚠️ Конвейер остановлен пользователем.")
            return False
        
        file_percent = int((idx / total_chunks) * 100)
        file_weight = 100 / total_files
        base_global_progress = current_file_idx * file_weight
        current_file_contribution = (idx / total_chunks) * file_weight
        global_percent = int(base_global_progress + current_file_contribution)
        
        progress_callback(file_percent, global_percent)
        
        raw_path = os.path.join(cfg["raw_dir"], file_name)
        processed_path = os.path.join(cfg["processed_dir"], file_name)
        
        if skip_llm:
            shutil.copy2(raw_path, processed_path)
        else:
            if os.path.exists(processed_path):
                log_callback(f"[{idx+1}/{total_chunks}] {file_name} уже обработан.")
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
                
                next_file_percent = int(((idx + 1) / total_chunks) * 100)
                next_global_percent = int(base_global_progress + (((idx + 1) / total_chunks) * file_weight))
                
                progress_callback(next_file_percent, next_global_percent)
                
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

def process_batch(file_list, global_cfg, progress_callback, log_callback, stop_check_callback, max_workers=1):
    """
    Функция управления пакетной обработкой списка файлов.
    """
    total_files = len(file_list)

    # Массив прогресса: каждый файл пишет свой 0-100
    file_progress = [0] * total_files
    lock = threading.Lock()

    def make_progress_cb(file_idx):
        """Фабрика коллбэков — каждый файл получает свой, изолированный."""
        def cb(chunk_pct, _global_ignored):
            with lock:
                file_progress[file_idx] = chunk_pct
                # Глобальный прогресс = среднее по всем файлам
                global_pct = int(sum(file_progress) / total_files)
            progress_callback(chunk_pct, global_pct, file_idx)
        return cb

    def process_one(i, file_path):
        file_name = os.path.basename(file_path)
        log_callback(f"====== 🚀 НАЧАЛО [{i+1}/{total_files}]: {file_name} ======")

        base_name_from_file = os.path.splitext(file_name)[0]
        parent_dir = os.path.dirname(file_path)

        if global_cfg["is_default_out"]:
            out_dir = os.path.join(parent_dir, base_name_from_file)
        else:
            out_dir = os.path.join(global_cfg["user_out_dir"], base_name_from_file)

        file_cfg = global_cfg.copy()
        file_cfg["src_file"] = file_path
        file_cfg["final_dir"] = out_dir
        file_cfg["raw_dir"] = os.path.join(out_dir, "raw")
        file_cfg["processed_dir"] = os.path.join(out_dir, "processed")

        return process_pipeline(
            file_cfg,
            progress_callback=make_progress_cb(i),
            log_callback=log_callback,
            stop_check_callback=stop_check_callback,
            current_file_idx=i,
            total_files=total_files
        )

    all_success = True

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_info = {
            executor.submit(process_one, i, fp): (i, os.path.basename(fp))
            for i, fp in enumerate(file_list)
        }

        for future in as_completed(future_to_info):
            i, file_name = future_to_info[future]
            try:
                result = future.result()
                if result is False:
                    all_success = False
                    log_callback(f"🛑 [{i+1}/{total_files}] {file_name} — остановлен.")
                else:
                    log_callback(f"====== ✅ ФАЙЛ ГОТОВ [{i+1}/{total_files}]: {file_name} ======\n")
            except Exception as e:
                all_success = False
                log_callback(f"💥 {file_name}: {e}\n⏭️ Переходим к следующему...\n")

    return all_success and not stop_check_callback()