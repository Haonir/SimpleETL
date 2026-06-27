import os
import sys
import threading
import time
import json
import docx
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import frontmatter
from openai import OpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

class SimpleETLApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SimpleETL - Text Processing & SPR Pipeline")
        self.root.geometry("1100x650")
        self.root.minsize(950, 550)
        self.CONFIG_FILE = "config.json"
        
        self.DEFAULT_PROMPT = (
            "Ты — эксперт по анализу данных и архитектор баз знаний. "
            "Твоя задача — преобразовать 'сырой' фрагмент текста в концентрированное представление формата SPR "
            "и упаковать его в YAML Front Matter.\n\n"
            "ИНСТРУКЦИЯ:\n"
            "1. Твой ответ ОБЯЗАТЕЛЬНО должен начинаться с блока YAML Front Matter, ограниченного тремя дефисами (---\n"
            "2. Внутри YAML блока строго следуй структуре SPR:\n"
            "   - title: [краткое техническое название фрагмента]\n"
            "   - концепция: [одно предложение-определение сути текста]\n"
            "   - алгоритм: [пошаговые действия, если есть в тексте, иначе 'отсутствует']\n"
            "   - формула: [если применимо математическое/логическое выражение, иначе 'не применимо']\n"
            "   - метафора: [яркая аналогия/сравнение на РУССКОМ языке]\n"
            "   - связи: [потенциальные ссылки на другие темы или разделы]\n"
            "   - теги: [список ключевых слов в формате [тег1, тег2]]\n"
            "3. Сразу после закрывающих дефисов (---) пиши очищенный, структурированный Markdown текст фрагмента.\n"
            "4. Не пиши никаких вводных фраз. Твой ответ должен начинаться прямо с `---`."
        )
        
        self.is_processing = False
        self.stop_requested = False
        
        # Создаем общее контекстное меню
        self.create_context_menu()
        
        # Создаем все виджеты
        self.create_widgets()
        
        # Загружаем настройки
        self.load_settings()
        
    def create_context_menu(self):
        """Создает контекстное меню"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Вырезать", command=lambda: self.current_widget.event_generate("<<Cut>>"))
        self.context_menu.add_command(label="Копировать", command=lambda: self.current_widget.event_generate("<<Copy>>"))
        self.context_menu.add_command(label="Вставить", command=lambda: self.current_widget.event_generate("<<Paste>>"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Выделить всё", command=self.select_all_handler)

    def show_context_menu(self, event):
        """Показывает меню в месте клика"""
        self.current_widget = event.widget
        self.current_widget.focus_set() # Принудительно ставим фокус на поле
        self.context_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def select_all_handler(self):
        if isinstance(self.current_widget, tk.Text):
            self.current_widget.tag_add("sel", "1.0", "end")
        else:
            self.current_widget.select_range(0, tk.END)

    def bind_edit_actions(self, widget):
        """Надежная принудительная привязка клавиш и мыши к конкретному виджету"""
        # Клик правой кнопкой
        widget.bind("<Button-3>", self.show_context_menu)
        widget.bind("<Button-2>", self.show_context_menu)
        
        # Горячие клавиши
        widget.bind("<Control-KeyPress>", self.universal_key_handler)
    
    def universal_key_handler(self, event):
        """Перехватчик системных кодов клавиш для Windows/Linux при любой раскладке"""
        widget = event.widget
        
        # event.keycode: 86 = V (М), 67 = C (С), 65 = A (Ф)
        if event.keycode == 86: # Вставка
            widget.event_generate("<<Paste>>")
            return "break"
        elif event.keycode == 67: # Копирование
            widget.event_generate("<<Copy>>")
            return "break"
        elif event.keycode == 65: # Выделить всё
            self.select_all_from_event(widget)
            return "break"
        elif event.keycode == 88: # Вырезать
            widget.event_generate("<<Cut>>")
            return "break"
        elif event.keycode == 90: # Отмена (Undo)
            widget.event_generate("<<Undo>>")
            return "break"

    def select_all_from_event(self, widget):
        if isinstance(widget, tk.Text):
            widget.tag_add("sel", "1.0", "end")
        else:
            widget.select_range(0, tk.END)
        return "break"

    def create_widgets(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#f5f6f8')
        style.configure('TLabelframe', background='#f5f6f8', relief='groove')
        style.configure('TLabelframe.Label', background='#f5f6f8', font=('Arial', 10, 'bold'))
        style.configure('TLabel', background='#f5f6f8', font=('Arial', 10))
        style.configure('Action.TButton', font=('Arial', 11, 'bold'), foreground='white', background='#2563eb')
        style.map('Action.TButton', background=[('active', '#1d4ed8'), ('disabled', '#93c5fd')])
        
        main_container = ttk.Frame(self.root, padding=10)
        main_container.pack(fill=tk.BOTH, expand=True)
        main_container.columnconfigure(0, weight=2)
        main_container.columnconfigure(1, weight=3)
        main_container.rowconfigure(0, weight=1)
        
        # --- ЛЕВАЯ ЧАСТЬ ---
        left_pane = ttk.Frame(main_container)
        left_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_pane.rowconfigure(0, weight=1)
        left_pane.rowconfigure(1, weight=1)
        left_pane.rowconfigure(2, weight=1)
        
        # 1. Выбор файлов
        lf_files = ttk.LabelFrame(left_pane, text=" Выбор входного файла / Input File Selection ")
        lf_files.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        lf_files.columnconfigure(1, weight=1)
        
        ttk.Label(lf_files, text="Исходный файл:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ent_src_file = ttk.Entry(lf_files)
        self.ent_src_file.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.bind_edit_actions(self.ent_src_file) # Привязка фикса
        ttk.Button(lf_files, text="Обзор", command=self.browse_src_file).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(lf_files, text="Выходная папка:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.ent_out_dir = ttk.Entry(lf_files)
        self.ent_out_dir.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.ent_out_dir.insert(0, "По умолчанию (папка с исходным файлом)")
        self.bind_edit_actions(self.ent_out_dir) # Привязка фикса
        ttk.Button(lf_files, text="Обзор", command=self.browse_out_dir).grid(row=1, column=2, padx=5, pady=5)
        
        ttk.Label(lf_files, text="Базовое имя чанков:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.ent_base_name = ttk.Entry(lf_files)
        self.ent_base_name.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        self.ent_base_name.insert(0, "chunk")
        self.bind_edit_actions(self.ent_base_name) # Привязка фикса
        
        # 2. Настройки подключения
        lf_prov = ttk.LabelFrame(left_pane, text=" Настройки провайдера LLM ")
        lf_prov.grid(row=1, column=0, sticky="nsew", pady=5)
        lf_prov.columnconfigure(1, weight=1)
        
        ttk.Label(lf_prov, text="Модель:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ent_model = ttk.Entry(lf_prov)
        self.ent_model.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.ent_model.insert(0, "llama3")
        self.bind_edit_actions(self.ent_model) # Привязка фикса
        
        ttk.Label(lf_prov, text="Base URL:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.ent_url = ttk.Entry(lf_prov)
        self.ent_url.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.ent_url.insert(0, "http://localhost:11434/v1")
        self.bind_edit_actions(self.ent_url) # Привязка фикса
        
        ttk.Label(lf_prov, text="API Key:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.ent_key = ttk.Entry(lf_prov, show="*")
        self.ent_key.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        self.ent_key.insert(0, "ollama")
        self.bind_edit_actions(self.ent_key) # Привязка фикса
        
        btn_save_cfg = ttk.Button(lf_prov, text="💾 Сохранить настройки", command=self.save_settings)
        btn_save_cfg.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=8)
        
        # 3. Кнопка и прогресс
        lf_actions = ttk.LabelFrame(left_pane, text=" Управление и прогресс ")
        lf_actions.grid(row=2, column=0, sticky="nsew", pady=(5, 0))
        lf_actions.columnconfigure(0, weight=1)
        
        self.btn_start = ttk.Button(lf_actions, text="▶ Начать обработку", style='Action.TButton', command=self.toggle_process)
        self.btn_start.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(lf_actions, text="Прогресс текущего чанка:").pack(anchor="w", padx=10, pady=(5, 0))
        self.progress_chunk = ttk.Progressbar(lf_actions, orient="horizontal", mode="determinate")
        self.progress_chunk.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(lf_actions, text="Общий прогресс конвейера:").pack(anchor="w", padx=10, pady=(5, 0))
        self.progress_total = ttk.Progressbar(lf_actions, orient="horizontal", mode="determinate")
        self.progress_total.pack(fill=tk.X, padx=10, pady=5)
        
        # --- ПРАВАЯ ЧАСТЬ ---
        right_pane = ttk.Frame(main_container)
        right_pane.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_pane.rowconfigure(0, weight=1)
        right_pane.rowconfigure(1, weight=1)
        
        # 1. Текст системного промпта
        lf_prompt = ttk.LabelFrame(right_pane, text=" Системный промпт / System Prompt ")
        lf_prompt.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        
        btn_reset_prompt = ttk.Button(lf_prompt, text="Сбросить на дефолтный SPR", command=self.reset_prompt)
        btn_reset_prompt.pack(anchor="e", padx=5, pady=2)
        
        self.txt_prompt = tk.Text(lf_prompt, font=("Courier New", 10), wrap=tk.WORD, height=10)
        self.txt_prompt.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.txt_prompt.insert(tk.END, self.DEFAULT_PROMPT)
        self.bind_edit_actions(self.txt_prompt) # Привязка фикса к текстовому полю
        
        # 2. Лог событий
        lf_logs = ttk.LabelFrame(right_pane, text=" Лог событий / Event Log ")
        lf_logs.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        
        self.txt_logs = tk.Text(lf_logs, background="#1e1e1e", foreground="#a9b7c6", font=("Consolas", 10), wrap=tk.WORD)
        self.txt_logs.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.bind_edit_actions(self.txt_logs) # Привязка фикса к логам (чтобы можно было копировать логи)
        
        scrollbar = ttk.Scrollbar(self.txt_logs, command=self.txt_logs.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_logs['yscrollcommand'] = scrollbar.set
        
        self.log("Система SimpleETL инициализирована. Ожидание выбора файла...")
        
    def log(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.txt_logs.insert(tk.END, f"{timestamp} {message}\n")
        self.txt_logs.see(tk.END)
    
    def save_settings(self):
        """Сохраняет текущие настройки и системный промпт из интерфейса в JSON файл"""
        config_data = {
            "model": self.ent_model.get(),
            "base_url": self.ent_url.get(),
            "api_key": self.ent_key.get(),
            "system_prompt": self.txt_prompt.get("1.0", tk.END).strip() # Забираем весь текст из виджета Text
        }
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            self.log("💾 Настройки провайдера и системный промпт успешно сохранены в config.json")
            messagebox.showinfo("Успех", "Все настройки и промпт сохранены!")
        except Exception as e:
            self.log(f"❌ Не удалось сохранить настройки: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл конфигурации: {e}")

    def load_settings(self):
        """Загружает настройки и промпт из JSON файла при старте приложения"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                
                # 1. Загружаем параметры провайдера
                self.ent_model.delete(0, tk.END)
                self.ent_url.delete(0, tk.END)
                self.ent_key.delete(0, tk.END)
                
                self.ent_model.insert(0, config_data.get("model", "llama3"))
                self.ent_url.insert(0, config_data.get("base_url", "http://localhost:11434/v1"))
                self.ent_key.insert(0, config_data.get("api_key", "ollama"))
                
                # 2. Загружаем системный промпт (если он есть в JSON, иначе берем дефолтный)
                saved_prompt = config_data.get("system_prompt")
                if saved_prompt:
                    self.txt_prompt.delete("1.0", tk.END)
                    self.txt_prompt.insert(tk.END, saved_prompt)
                    self.log("📂 Конфигурация и кастомный системный промпт успешно загружены.")
                else:
                    self.log("📂 Конфигурация загружена. Используется стандартный системный промпт.")
                    
            except Exception as e:
                self.log(f"⚠️ Ошибка при чтении config.json: {e}. Используются дефолтные значения.")
        else:
            self.log("ℹ️ Файл конфигурации config.json не найден. Будут использованы стандартные настройки.")
        
    def browse_src_file(self):
        filetypes = [
            ("Поддерживаемые файлы", "*.txt *.md *.docx *.doc"),
            ("Документы Word", "*.docx *.doc"),
            ("Текстовые файлы", "*.txt *.md"),
            ("Все файлы", "*.*")
        ]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            self.ent_src_file.delete(0, tk.END)
            self.ent_src_file.insert(0, filename)
            base = os.path.splitext(os.path.basename(filename))[0]
            self.ent_base_name.delete(0, tk.END)
            self.ent_base_name.insert(0, f"{base}_chunk")
            self.log(f"Выбран исходный файл: {filename}")
            
    def browse_out_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.ent_out_dir.delete(0, tk.END)
            self.ent_out_dir.insert(0, directory)
            self.log(f"Выбрана папка сохранения: {directory}")
            
    def reset_prompt(self):
        self.txt_prompt.delete("1.0", tk.END)
        self.txt_prompt.insert(tk.END, self.DEFAULT_PROMPT)
        self.log("Промпт сброшен к стандартному SPR шаблону.")
        
    def toggle_process(self):
        if self.is_processing:
            self.stop_requested = True
            self.log("Запрошена остановка конвейера... Дождитесь завершения текущего чанка.")
            self.btn_start.configure(state=tk.DISABLED)
        else:
            self.start_pipeline()
            
    def start_pipeline(self):
        src_file = self.ent_src_file.get()
        if not src_file or not os.path.exists(src_file):
            messagebox.showerror("Ошибка", "Укажите существующий исходный файл!")
            return
            
        out_dir = self.ent_out_dir.get()
        if out_dir == "По умолчанию (папка с исходным файлом)" or not out_dir.strip():
            out_dir = os.path.dirname(src_file)
            
        raw_dir = os.path.join(out_dir, "raw_chunks")
        processed_dir = os.path.join(out_dir, "processed_chunks")
        final_dir = os.path.join(out_dir, "ready_for_webui")
        
        config = {
            "src_file": src_file,
            "raw_dir": raw_dir,
            "processed_dir": processed_dir,
            "final_dir": final_dir,
            "base_name": self.ent_base_name.get(),
            "model": self.ent_model.get(),
            "url": self.ent_url.get(),
            "key": self.ent_key.get(),
            "prompt": self.txt_prompt.get("1.0", tk.END).strip()
        }
        
        self.is_processing = True
        self.stop_requested = False
        self.btn_start.configure(text="🛑 Остановить обработку")
        
        threading.Thread(target=self.pipeline_thread_worker, args=(config,), daemon=True).start()
        
    def pipeline_thread_worker(self, cfg):
        try:
            # === ЭТАП 1 ===
            self.log("--- ЭТАП 1: Нарезка файла ---")
            if not os.path.exists(cfg["raw_dir"]):
                os.makedirs(cfg["raw_dir"])
                
            # Проверяем расширение файла
            ext = os.path.splitext(cfg["src_file"])[1].lower()
            
            if ext in [".docx", ".doc"]:
                self.log("Чтение документа Word...")
                try:
                    doc = docx.Document(cfg["src_file"])
                    # Собираем весь текст из параграфов, разделяя их переносом строки
                    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                except Exception as doc_err:
                    # Если .doc старого формата, python-docx может выдать ошибку
                    raise Exception(f"Не удалось прочитать Word файл. Если это старый формат .doc, пересохраните его в .docx: {doc_err}")
            else:
                # Обычное чтение для .txt и .md
                with open(cfg["src_file"], 'r', encoding='utf-8') as f:
                    text = f.read()
            
            if not text.strip():
                raise Exception("Файл пуст или не содержит читаемого текста!")

            splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1500, length_function=len)
            chunks = splitter.split_text(text)
            total_chunks = len(chunks)
            self.log(f"Текст успешно извлечен и нарезан на {total_chunks} кусков.")
            
            for i, chunk_data in enumerate(chunks):
                chunk_file = os.path.join(cfg["raw_dir"], f"{cfg['base_name']}_{i:03d}.txt")
                with open(chunk_file, 'w', encoding='utf-8') as f_out:
                    f_out.write(chunk_data)
                    
            # === ЭТАП 2 ===
            self.log("--- ЭТАП 2: Анализ SPR через LLM ---")
            if not os.path.exists(cfg["processed_dir"]):
                os.makedirs(cfg["processed_dir"])
                
            client = OpenAI(base_url=cfg["url"], api_key=cfg["key"])
            raw_files = sorted([f for f in os.listdir(cfg["raw_dir"]) if f.startswith(cfg["base_name"])])
            
            self.progress_total["maximum"] = total_chunks
            
            for idx, file_name in enumerate(raw_files):
                if self.stop_requested:
                    self.log("⚠️ Конвейер остановлен пользователем.")
                    break
                    
                self.progress_chunk["value"] = 30
                self.root.update_idletasks()
                
                raw_path = os.path.join(cfg["raw_dir"], file_name)
                processed_path = os.path.join(cfg["processed_dir"], file_name)
                
                if os.path.exists(processed_path):
                    self.log(f"[{idx+1}/{total_chunks}] {file_name} уже обработан.")
                    self.progress_total["value"] = idx + 1
                    continue
                    
                with open(raw_path, 'r', encoding='utf-8') as f:
                    chunk_text = f.read()
                    
                self.log(f"[{idx+1}/{total_chunks}] Запрос к LLM ({cfg['model']})...")
                
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
                        
                    self.progress_chunk["value"] = 100
                    self.progress_total["value"] = idx + 1
                    self.root.update_idletasks()
                    
                except Exception as ex:
                    self.log(f"❌ Ошибка LLM на чанке {file_name}: {ex}")
                    break
                    
            # === ЭТАП 3 ===
            if not self.stop_requested:
                self.log("--- ЭТАП 3: Упаковка под Open WebUI ---")
                if not os.path.exists(cfg["final_dir"]):
                    os.makedirs(cfg["final_dir"])
                    
                processed_files = sorted([f for f in os.listdir(cfg["processed_dir"]) if f.startswith(cfg["base_name"])])
                
                for file_name in processed_files:
                    proc_path = os.path.join(cfg["processed_dir"], file_name)
                    
                    with open(proc_path, 'r', encoding='utf-8') as f:
                        raw_content = f.read()
                    
                    # Безопасный разбор через try-except, чтобы кривой YAML не вешал программу
                    try:
                        parsed = frontmatter.loads(raw_content)
                        metadata = parsed.metadata
                        content = parsed.content
                    except Exception as yaml_err:
                        self.log(f"⚠️ Ошибка YAML в файле {file_name}. Применяем резервный парсер...")
                        # Резервный вариант: если YAML сломан, пытаемся вырезать его регулярками или просто берем весь текст
                        metadata = {}
                        content = raw_content
                        # Пытаемся грубо вытащить title и концепцию через поиск строк
                        for line in raw_content.split('\n'):
                            if line.startswith('title:') or line.startswith('- title:'):
                                metadata['title'] = line.split(':', 1)[1].strip().strip('"\'')
                            elif line.startswith('концепция:') or line.startswith('- концепция:'):
                                metadata['концепция'] = line.split(':', 1)[1].strip().strip('"\'')

                    # Извлекаем данные (с дефолтными значениями, если их нет)
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
                    
                    # 1. Очищаем заголовок от мусора
                    clean_title = "".join([c if c.isalnum() or c in " _-" else "" for c in title]).strip()
                    clean_title = clean_title.replace(" ", "_")
                    
                    # 2. Умная обрезка по словам (максимум ~40 символов для сути заголовка)
                    max_len = 40
                    if len(clean_title) > max_len:
                        # Режем с запасом и ищем последний знак подчеркивания, чтобы не рвать слова
                        truncated = clean_title[:max_len]
                        if "_" in truncated:
                            clean_title = truncated.rsplit("_", 1)[0]
                        else:
                            clean_title = truncated
                    
                    # 3. Формируем финальное имя: Номер_СутьЗаголовка.md
                    # Берем индекс из цикла (например, 0 -> "01", 1 -> "02")
                    file_idx = processed_files.index(file_name) + 1
                    final_filename = f"{file_idx:02d}_{clean_title}.md"
                    
                    # Записываем результат
                    with open(os.path.join(cfg["final_dir"], final_filename), 'w', encoding='utf-8') as f_out:
                        f_out.write(new_content)
                        
                self.log(f"🎉 Завершено! Результаты сохранены в: {cfg['final_dir']}")
                messagebox.showinfo("Успех", f"SPR-документы созданы в папке:\n{cfg['final_dir']}")
                
        except Exception as e:
            self.log(f"💥 Критическая ошибка конвейера: {e}")
            messagebox.showerror("Ошибка", str(e))
            
        finally:
            self.is_processing = False
            self.btn_start.configure(text="▶ Начать обработку", state=tk.NORMAL)
            self.progress_chunk["value"] = 0
            self.progress_total["value"] = 0

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleETLApp(root)
    root.mainloop()