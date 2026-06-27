import os
import sys
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import config_manager
import etl_pipeline

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Для отладки
# print(f"Рабочая директория: {os.getcwd()}")
# print(f"Директория скрипта: {os.path.dirname(os.path.abspath(__file__))}")

class SimpleETLApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SimpleETL - Text Processing & SPR Pipeline")
        self.root.geometry("1100x650")
        self.root.minsize(950, 550)
        
        self.DEFAULT_PROMPT = (
            "Ты — эксперт по анализу данных и архитектор баз знаний. Твоя задача — преобразовать 'сырой' фрагмент текста в концентрированное представление формата SPR и упаковать его в YAML Front Matter.\n\n"
            "ИНСТРУКЦИЯ ПО ФОРМАТУ:\n"
            "1. Твой ответ ОБЯЗАТЕЛЬНО должен начинаться с блока YAML Front Matter, ограниченного тремя дефисами (---\n"
            "2. Внутри YAML блока СТРОГО оборачивай текстовые значения после двоеточий в двойные кавычки `\"`. Это критически важно для предотвращения ошибок синтаксиса!\n"
            "3. НЕ используй знаки доллара ($) и LaTeX-разметку (например, \\leftrightarrow) внутри YAML блока. Заменяй их на текстовые аналоги (например, <->).\n\n"
            "СТРУКТУРА YAML (строго в кавычках):\n"
            "   - title: \"[краткое техническое название фрагмента]\"\n"
            "   - концепция: \"[одно предложение-определение сути текста]\"\n"
            "   - алгоритм: \"[пошаговые действия через запятую или цифры]\"\n"
            "   - формула: \"[математическое/логическое выражение текстом без знаков $]\"\n"
            "   - метафора: \"[яркая аналогия/сравнение на РУССКОМ языке]\"\n"
            "   - связи: [\"Связь1\", \"Связь2\"]\n"
            "   - теги: [\"тег1\", \"тег2\"]\n\n"
            "4. Сразу после закрывающих дефисов (---) пиши очищенный, структурированный Markdown текст фрагмента.\n"
            "5. Не пиши никаких вводных фраз. Твой ответ должен начинаться прямо с `---`."
        )
        
        self.is_processing = False
        self.stop_requested = False
        
        self.create_context_menu()
        self.create_widgets()
        
        self.prompts_library = {}
        
        # Загружаем настройки из внешнего менеджера конфигураций
        self.load_settings()
        
    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Вырезать", command=lambda: self.current_widget.event_generate("<<Cut>>"))
        self.context_menu.add_command(label="Копировать", command=lambda: self.current_widget.event_generate("<<Copy>>"))
        self.context_menu.add_command(label="Вставить", command=lambda: self.current_widget.event_generate("<<Paste>>"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Выделить всё", command=self.select_all_handler)

    def show_context_menu(self, event):
        self.current_widget = event.widget
        self.current_widget.focus_set()
        self.context_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def select_all_handler(self):
        if isinstance(self.current_widget, tk.Text):
            self.current_widget.tag_add("sel", "1.0", "end")
        else:
            self.current_widget.select_range(0, tk.END)

    def bind_edit_actions(self, widget):
        widget.bind("<Button-3>", self.show_context_menu)
        widget.bind("<Button-2>", self.show_context_menu)
        widget.bind("<Control-KeyPress>", self.universal_key_handler)
        
    def universal_key_handler(self, event):
        widget = event.widget
        if event.keycode == 86:    # V
            widget.event_generate("<<Paste>>")
            return "break"
        elif event.keycode == 67:  # C
            widget.event_generate("<<Copy>>")
            return "break"
        elif event.keycode == 65:  # A
            self.select_all_from_event(widget)
            return "break"
        elif event.keycode == 88:  # X
            widget.event_generate("<<Cut>>")
            return "break"
        elif event.keycode == 90:  # Z
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
        
        # Разные веса колонок для устранения зазоров
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
        self.bind_edit_actions(self.ent_src_file)
        ttk.Button(lf_files, text="Обзор", command=self.browse_src_file).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(lf_files, text="Выходная папка:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.ent_out_dir = ttk.Entry(lf_files)
        self.ent_out_dir.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.ent_out_dir.insert(0, "По умолчанию (папка с исходным файлом)")
        self.bind_edit_actions(self.ent_out_dir)
        ttk.Button(lf_files, text="Обзор", command=self.browse_out_dir).grid(row=1, column=2, padx=5, pady=5)
        
        ttk.Label(lf_files, text="Базовое имя чанков:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.ent_base_name = ttk.Entry(lf_files)
        self.ent_base_name.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        self.ent_base_name.insert(0, "chunk")
        self.bind_edit_actions(self.ent_base_name)
        
        # 2. Настройки подключения
        lf_prov = ttk.LabelFrame(left_pane, text=" Настройки провайдера LLM ")
        lf_prov.grid(row=1, column=0, sticky="nsew", pady=5)
        lf_prov.columnconfigure(1, weight=1)
        
        ttk.Label(lf_prov, text="Модель:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ent_model = ttk.Entry(lf_prov)
        self.ent_model.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.bind_edit_actions(self.ent_model)
        
        ttk.Label(lf_prov, text="Base URL:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.ent_url = ttk.Entry(lf_prov)
        self.ent_url.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        self.bind_edit_actions(self.ent_url)
        
        ttk.Label(lf_prov, text="API Key:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.ent_key = ttk.Entry(lf_prov, show="*")
        self.ent_key.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        self.bind_edit_actions(self.ent_key)
        
        btn_save_cfg = ttk.Button(lf_prov, text="💾 Сохранить настройки", command=self.save_settings)
        btn_save_cfg.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=8)
        
        # 3. Кнопка и прогресс
        self.var_cleanup = tk.BooleanVar(value=True)
               
        lf_actions = ttk.LabelFrame(left_pane, text=" Управление и прогресс ")
        lf_actions.grid(row=2, column=0, sticky="nsew", pady=(5, 0))
        
        self.btn_start = ttk.Button(lf_actions, text="▶ Начать обработку", style='Action.TButton', command=self.toggle_process)
        self.btn_start.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Checkbutton(lf_actions, text="Удалять временные файлы после завершения", variable=self.var_cleanup).pack(anchor="w", padx=10, pady=(0, 5))
        
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
        
        lf_prompt = ttk.LabelFrame(right_pane, text=" Системный промпт / System Prompt ")
        lf_prompt.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        
        prompt_mgmt_frame = ttk.Frame(lf_prompt)
        prompt_mgmt_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(prompt_mgmt_frame, text="Шаблон:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.cb_prompt_templates = ttk.Combobox(prompt_mgmt_frame, state="readonly", width=30)
        self.cb_prompt_templates.pack(side=tk.LEFT, padx=(0, 5))
        self.cb_prompt_templates.bind("<<ComboboxSelected>>", self.on_prompt_template_changed)
        
        btn_add_prompt = ttk.Button(prompt_mgmt_frame, text="➕ Сохранить как...", command=self.save_prompt_as_new)
        btn_add_prompt.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_reset_prompt = ttk.Button(prompt_mgmt_frame, text="Сброс", width=8, command=self.reset_prompt)
        btn_reset_prompt.pack(side=tk.RIGHT)
        
        self.txt_prompt = tk.Text(lf_prompt, font=("Courier New", 10), wrap=tk.WORD, height=10)
        self.txt_prompt.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.bind_edit_actions(self.txt_prompt)
        
        lf_logs = ttk.LabelFrame(right_pane, text=" Лог событий / Event Log ")
        lf_logs.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        
        self.txt_logs = tk.Text(lf_logs, background="#1e1e1e", foreground="#a9b7c6", font=("Consolas", 10), wrap=tk.WORD)
        self.txt_logs.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.bind_edit_actions(self.txt_logs)
        
        scrollbar = ttk.Scrollbar(self.txt_logs, command=self.txt_logs.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_logs['yscrollcommand'] = scrollbar.set
        
    def log(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.txt_logs.insert(tk.END, f"{timestamp} {message}\n")
        self.txt_logs.see(tk.END)
        
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
    
    def on_prompt_template_changed(self, event):
        """Срабатывает при выборе другого промпта в выпадающем списке"""
        selected_name = self.cb_prompt_templates.get()
        if selected_name in self.prompts_library:
            self.txt_prompt.delete("1.0", tk.END)
            self.txt_prompt.insert(tk.END, self.prompts_library[selected_name])
            self.log(f"🔄 Переключено на промпт: '{selected_name}'")

    def save_prompt_as_new(self):
        """Открывает модальное окно для ввода имени и сохраняет текущий текст промпта как новый шаблон"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Новый шаблон")
        dialog.geometry("350x120")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Введите название для этого промпта:").pack(anchor="w", padx=10, pady=10)
        ent_name = ttk.Entry(dialog)
        ent_name.pack(fill=tk.X, padx=10, pady=5)
        ent_name.focus_set()
        
        def confirm():
            name = ent_name.get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Имя не может быть пустым!", parent=dialog)
                return
            
            current_text = self.txt_prompt.get("1.0", tk.END).strip()
            
            self.prompts_library[name] = current_text
            
            self.cb_prompt_templates['values'] = list(self.prompts_library.keys())
            self.cb_prompt_templates.set(name)
            
            self.log(f"➕ Добавлен новый шаблон промпта: '{name}'")
            dialog.destroy()
            
            self.save_settings()

        ttk.Button(dialog, text="Сохранить", command=confirm).pack(anchor="e", padx=10, pady=5)
            
    def reset_prompt(self):
        self.txt_prompt.delete("1.0", tk.END)
        self.txt_prompt.insert(tk.END, self.DEFAULT_PROMPT)
        self.log("Промпт сброшен к стандартному SPR шаблону.")
        
    def save_settings(self):
        try:
            current_name = self.cb_prompt_templates.get()
            if not current_name:
                current_name = "Дефолтный SPR"
                
            # Обновляем текст текущего промпта в нашей библиотеке перед сохранением файла
            self.prompts_library[current_name] = self.txt_prompt.get("1.0", tk.END).strip()
            
            config_manager.save_config(
                model=self.ent_model.get(),
                base_url=self.ent_url.get(),
                api_key=self.ent_key.get(),
                prompts_dict=self.prompts_library,
                current_prompt_name=current_name
            )
            self.log("💾 Все настройки приложения и библиотека промптов успешно сохранены.")
            messagebox.showinfo("Успех", "Все настройки сохранены!")
        except Exception as e:
            self.log(f"❌ Не удалось сохранить настройки: {e}")
            messagebox.showerror("Ошибка", str(e))

    def load_settings(self):
        cfg = config_manager.load_config()
        
        # Загружаем базовые параметры LLM
        self.ent_model.delete(0, tk.END)
        self.ent_url.delete(0, tk.END)
        self.ent_key.delete(0, tk.END)
        
        if cfg:
            self.ent_model.insert(0, cfg.get("model", "llama3"))
            self.ent_url.insert(0, cfg.get("base_url", "http://localhost:11434/v1"))
            self.ent_key.insert(0, cfg.get("api_key", "ollama"))
            
            # Восстанавливаем библиотеку промптов из JSON
            self.prompts_library = cfg.get("prompts", {})
            
            # Если в конфиге ничего нет, создаем дефолтную запись
            if not self.prompts_library:
                self.prompts_library = {"Дефолтный SPR": self.DEFAULT_PROMPT}
                
            # Определяем, какой промпт выбрать активным
            active_prompt_name = cfg.get("current_prompt_name")
            if not active_prompt_name or active_prompt_name not in self.prompts_library:
                active_prompt_name = list(self.prompts_library.keys())[0]
                
            # Обновляем выпадающий список
            self.cb_prompt_templates['values'] = list(self.prompts_library.keys())
            self.cb_prompt_templates.set(active_prompt_name)
            
            # Выводим текст промпта на экран
            self.txt_prompt.delete("1.0", tk.END)
            self.txt_prompt.insert(tk.END, self.prompts_library[active_prompt_name])
            
            self.log(f"📂 Конфигурация успешно загружена из: {config_manager.CONFIG_FILE}")
        else:
            # Если файла конфигурации вообще нет (первый запуск)
            self.ent_model.insert(0, "llama3")
            self.ent_url.insert(0, "http://localhost:11434/v1")
            self.ent_key.insert(0, "ollama")
            
            self.prompts_library = {"Дефолтный SPR": self.DEFAULT_PROMPT}
            self.cb_prompt_templates['values'] = list(self.prompts_library.keys())
            self.cb_prompt_templates.set("Дефолтный SPR")
            
            self.txt_prompt.insert(tk.END, self.DEFAULT_PROMPT)
            self.log(f"ℹ️ Конфиг не найден в {BASE_DIR}. Загружены дефолтные параметры.")

    def toggle_process(self):
        if self.is_processing:
            self.stop_requested = True
            self.log("Запрошена остановка конвейера... Ожидание завершения чанка.")
            self.btn_start.configure(state=tk.DISABLED)
        else:
            self.start_pipeline()
            
    def start_pipeline(self):
        src_file = self.ent_src_file.get().strip()
        if not src_file or not os.path.exists(src_file):
            messagebox.showerror("Ошибка", "Укажите исходный файл!")
            return
        
        if not os.path.isabs(src_file):
            src_file = os.path.abspath(os.path.join(BASE_DIR, src_file))
            
        if not os.path.exists(src_file):
            messagebox.showerror("Ошибка", f"Файл не найден по пути:\n{src_file}")
            return    
        
        base_name_from_file = os.path.splitext(os.path.basename(src_file))[0]
        parent_dir = os.path.dirname(src_file)
        
        user_out_dir = self.ent_out_dir.get().strip()
        if user_out_dir == "По умолчанию (папка с исходным файлом)" or not user_out_dir:
            out_dir = os.path.join(parent_dir, base_name_from_file)
        else:
            # Если пользователь ввел свой путь, проверяем абсолютный ли он
            if not os.path.isabs(user_out_dir):
                out_dir = os.path.abspath(os.path.join(BASE_DIR, user_out_dir))
            else:
                out_dir = user_out_dir
            
        config = {
            "src_file": src_file,
            "raw_dir": os.path.join(out_dir, "raw"),
            "processed_dir": os.path.join(out_dir, "processed"),
            "final_dir": out_dir,
            "base_name": self.ent_base_name.get().strip() or "chunk",
            "model": self.ent_model.get(),
            "url": self.ent_url.get(),
            "key": self.ent_key.get(),
            "prompt": self.txt_prompt.get("1.0", tk.END).strip(),
            "cleanup": self.var_cleanup.get()
        }
        
        self.is_processing = True
        self.stop_requested = False
        self.btn_start.configure(text="🛑 Остановить обработку", state=tk.NORMAL)
        
        # Запускаем конвейер
        threading.Thread(target=self.thread_worker, args=(config,), daemon=True).start()

    def thread_worker(self, cfg):
        try:
            # Вызываем функцию конвейера из отдельного модуля etl_pipeline
            success = etl_pipeline.process_pipeline(
                cfg=cfg,
                progress_callback=self.update_progress,
                log_callback=self.log,
                stop_check_callback=lambda: self.stop_requested
            )
            
            if success:
                self.progress_total["value"] = 100
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

    def update_progress(self, chunk_val, total_val):
        """Обновление прогресс-баров из фонового потока (принимает значения от 0 до 100)"""
        self.progress_chunk["value"] = chunk_val
        if total_val is not None:
            self.progress_total["value"] = total_val
        self.root.update_idletasks()

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleETLApp(root)
    root.mainloop()