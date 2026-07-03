import os
import sys
import threading
import tkinter as tk
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, messagebox

from . import config_manager
from . import etl_pipeline

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Цветовая палитра ──
BG_MAIN    = '#eef1f5'
BG_CARD    = '#ffffff'
BG_INPUT   = '#ffffff'
FG_TITLE   = '#1a1a2e'
FG_LABEL   = '#374151'
FG_HEADER  = '#2c323a'
BORDER     = '#d1d5db'
ACCENT     = '#3b82f6'
ACCENT_HOV = '#2563eb'
ACCENT_DIS = '#93c5fd'
BTN_BG     = '#e5e7eb'
BTN_FG     = '#1f2937'
BTN_HOVER  = '#d1d5db'

# ── Шрифты ──
FONT_LABEL  = ("Segoe UI", 12)
FONT_HEADER = ("Segoe UI", 14, "bold")
FONT_BTN    = ("Segoe UI", 11)
FONT_BTN_SM = ("Segoe UI", 11, "bold")
FONT_MONO   = ("Cascadia Mono", 12)
FONT_MONO_9 = ("Consolas", 11)


# ═══════════════════════════════════════════════════════════════
#  FileListBox — кастомный список файлов на базе CTkScrollableFrame
# ═══════════════════════════════════════════════════════════════
class FileListBox(ctk.CTkFrame):
    def __init__(self, master, height=4, on_hover=None, on_leave=None, on_select=None, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._items = []          # [(frame, label, path)]
        self._selected = set()
        self._on_hover = on_hover
        self._on_leave = on_leave
        self._on_select = on_select

        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_CARD, corner_radius=8,
            border_width=1, border_color=BORDER,
            height=max(height * 28, 120))
        self._scroll.pack(fill="both", expand=True)

    # ── публичный API (совместимый с tk.Listbox) ──
    def insert(self, path):
        idx = len(self._items)
        frame = ctk.CTkFrame(self._scroll, fg_color="transparent",
                             corner_radius=4, height=26)
        frame.pack(fill="x", padx=3, pady=1)
        frame.pack_propagate(False)

        lbl = ctk.CTkLabel(frame, text=os.path.basename(path), anchor="w",
                           font=FONT_BTN, text_color=FG_TITLE)
        lbl.pack(side="left", fill="x", expand=True, padx=8, pady=2)

        def _click(e, f=frame): self._select_by_frame(f, e)
        def _enter(e, f=frame): self._fire_hover(f, e)
        def _leave(e):          self._fire_leave()

        for w in (frame, lbl):
            w.bind("<Button-1>", _click)
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)

        self._items.append((frame, lbl, path))
        return idx

    def delete(self, index):
        if 0 <= index < len(self._items):
            self._items[index][0].destroy()
            self._items.pop(index)
            self._selected.discard(index)
            self._selected = {i - (1 if i > index else 0) for i in self._selected}

    def get(self, index):
        return self._items[index][2]

    def size(self):
        return len(self._items)

    def curselection(self):
        return sorted(self._selected)

    def clear(self):
        for f, _, _ in self._items:
            f.destroy()
        self._items.clear()
        self._selected.clear()

    # ── внутреннее ──
    def _find(self, target):
        for i, (f, _, _) in enumerate(self._items):
            if f is target:
                return i
        return -1

    def _select_by_frame(self, frame, event):
        idx = self._find(frame)
        if idx < 0:
            return
        if event.state & 0x4:                       # Ctrl
            self._selected.symmetric_difference_update({idx})
        else:
            self._selected = {idx}
        self._paint()
        if self._on_select:
            self._on_select(idx)

    def _paint(self):
        for i, (f, lbl, _) in enumerate(self._items):
            sel = i in self._selected
            f.configure(fg_color=ACCENT if sel else "transparent")
            lbl.configure(text_color="white" if sel else FG_TITLE)

    def _fire_hover(self, frame, event):
        if self._on_hover:
            idx = self._find(frame)
            if idx >= 0:
                self._on_hover(idx, event)

    def _fire_leave(self):
        if self._on_leave:
            self._on_leave()


# ═══════════════════════════════════════════════════════════════
#  SimpleETLApp
# ═══════════════════════════════════════════════════════════════
class SimpleETLApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SimpleETL - Text Processing & SPR Pipeline")
        self.root.geometry("1100x630")
        self.root.minsize(1000, 630)
        self.root.configure(fg_color=BG_MAIN)

        self.DEFAULT_OUT_PLACEHOLDER = "(Опционально)"

        self.DEFAULT_PROMPT = (
            "Ты — эксперт по анализу данных и архитектор баз знаний. Твоя задача — "
            "преобразовать 'сырой' фрагмент текста в концентрированное представление "
            "формата SPR и упаковать его в YAML Front Matter.\n\n"
            "ИНСТРУКЦИЯ ПО ФОРМАТУ:\n"
            "1. Твой ответ ОБЯЗАТЕЛЬНО должен начинаться с блока YAML Front Matter, "
            "ограниченного тремя дефисами (---\n"
            "2. Внутри YAML блока СТРОГО оборачивай текстовые значения после двоеточий "
            "в двойные кавычки \". Это критически важно для предотвращения ошибок синтаксиса!\n"
            "3. НЕ используй знаки доллара ($) и LaTeX-разметку (например, \\leftrightarrow) "
            "внутри YAML блока. Заменяй их на текстовые аналоги (например, <->).\n\n"
            "СТРУКТУРА YAML (строго в кавычках):\n"
            '   - title: "[краткое техническое название фрагмента]"\n'
            '   - концепция: "[одно предложение-определение сути текста]"\n'
            '   - алгоритм: "[пошаговые действия через запятую или цифры]"\n'
            '   - формула: "[математическое/логическое выражение текстом без знаков $]"\n'
            '   - метафора: "[яркая аналогия/сравнение на РУССКОМ языке]"\n'
            '   - связи: ["Связь1", "Связь2"]\n'
            '   - теги: ["тег1", "тег2"]\n\n'
            "4. Сразу после закрывающих дефисов (---) пиши очищенный, структурированный "
            "Markdown текст фрагмента.\n"
            "5. Не пиши никаких вводных фраз. Твой ответ должен начинаться прямо с `---`."
        )

        self.is_processing = False
        self.stop_requested = False
        self.file_paths = []
        self._tooltip_window = None
        self.prompts_library = {}
        self.file_progress = {}       # {file_path: chunk_pct (0-100)}
        self._watched_file_idx = None  # индекс файла, прогресс которого отображается

        self.create_widgets()
        self.load_settings()

    # ──────────────────────────────────────────────────────────
    #  Утилиты
    # ──────────────────────────────────────────────────────────
    def _card_section(self, parent, title):
        """Белая карточка с заголовком — замена LabelFrame."""
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10,
                            border_width=1, border_color=BORDER)
        ctk.CTkLabel(card, text=title, anchor="w", font=FONT_HEADER,
                     text_color=FG_HEADER).pack(fill="x", padx=12, pady=(10, 2))
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        return card, content

    @staticmethod
    def _btn_kw(**extra):
        """Базовые параметры для обычных кнопок."""
        d = dict(corner_radius=8, height=34, font=FONT_BTN,
                 fg_color=BTN_BG, hover_color=BTN_HOVER, text_color=BTN_FG)
        d.update(extra)
        return d

    def _get_tk_widget(self, widget):
        """Вернуть базовый tkinter-виджет из CTk-обёртки."""
        if hasattr(widget, "textbox"):
            return widget.textbox
        if hasattr(widget, "entry"):
            return widget.entry
        return widget

    # ──────────────────────────────────────────────────────────
    #  Контекстное меню / горячие клавиши
    # ──────────────────────────────────────────────────────────
    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(
            label="Вырезать",
            command=lambda: self._get_tk_widget(self.current_widget).event_generate("<<Cut>>"))
        self.context_menu.add_command(
            label="Копировать",
            command=lambda: self._get_tk_widget(self.current_widget).event_generate("<<Copy>>"))
        self.context_menu.add_command(
            label="Вставить",
            command=lambda: self._get_tk_widget(self.current_widget).event_generate("<<Paste>>"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Выделить всё", command=self.select_all_handler)

    def show_context_menu(self, event):
        self.current_widget = event.widget
        self.current_widget.focus_set()
        self.context_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def select_all_handler(self):
        w = self.current_widget
        if isinstance(w, ctk.CTkTextbox):
            w.textbox.tag_add("sel", "1.0", "end")
        elif isinstance(w, tk.Text):
            w.tag_add("sel", "1.0", "end")
        elif isinstance(w, ctk.CTkEntry):
            w.entry.select_range(0, "end")
        elif isinstance(w, tk.Entry):
            w.select_range(0, "end")

    def bind_edit_actions(self, widget):
        widget.bind("<Button-3>", self.show_context_menu)
        widget.bind("<Button-2>", self.show_context_menu)
        widget.bind("<Control-KeyPress>", self.universal_key_handler)

    def universal_key_handler(self, event):
        tk_w = self._get_tk_widget(event.widget)
        key = event.keycode
        if key == 86:
            tk_w.event_generate("<<Paste>>")
        elif key == 67:
            tk_w.event_generate("<<Copy>>")
        elif key == 65:
            self.select_all_handler()
        elif key == 88:
            tk_w.event_generate("<<Cut>>")
        elif key == 90:
            tk_w.event_generate("<<Undo>>")
        return "break"

    # ──────────────────────────────────────────────────────────
    #  Tooltip
    # ──────────────────────────────────────────────────────────
    def _show_tooltip(self, index, event):
        if index < 0 or index >= len(self.file_paths):
            return
        self._hide_tooltip()
        x, y = event.x_root + 15, event.y_root + 15
        tw = tk.Toplevel(self.root)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.file_paths[index], background="#ffffe0",
                 foreground="#000000", font=FONT_MONO_9,
                 padx=6, pady=2, relief="solid", borderwidth=1).pack()
        self._tooltip_window = tw

    def _hide_tooltip(self, _=None):
        if self._tooltip_window:
            self._tooltip_window.destroy()
            self._tooltip_window = None

    # ──────────────────────────────────────────────────────────
    #  Построение интерфейса
    # ──────────────────────────────────────────────────────────
    def create_widgets(self):
        self.create_context_menu()

        main = ctk.CTkFrame(self.root, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=10)
        main.grid_columnconfigure(0, weight=0)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # ─── ЛЕВАЯ ЧАСТЬ (скроллируемая) ─────────────────────
        left_scroll = ctk.CTkScrollableFrame(main, fg_color="transparent",
                                              width=400, corner_radius=0,
                                              border_width=0)
        left_scroll.grid(row=0, column=0, sticky="ns", padx=(0, 0))

        # — Файлы —
        lf_files, fc = self._card_section(left_scroll, "Файлы для обработки")
        lf_files.pack(fill="x", pady=(0, 5))

        self.file_list = FileListBox(
            fc, height=4,
            on_hover=self._show_tooltip, on_leave=self._hide_tooltip,
            on_select=self._on_file_select)
        self.file_list.pack(fill="both", expand=True, pady=(0, 4))

        bf = ctk.CTkFrame(fc, fg_color="transparent")
        bf.pack(fill="x", pady=(0, 4))
        btn_row = ctk.CTkFrame(bf, fg_color="transparent")
        btn_row.pack(anchor="center")
        ctk.CTkButton(btn_row, text="➕ Добавить", command=self.browse_src_file,
                       **self._btn_kw(width=110)).pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_row, text="✖ Удалить", command=self.remove_selected_files,
                       **self._btn_kw(width=100)).pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_row, text="🗑 Очистить", command=self.clear_files,
                       **self._btn_kw(width=100)).pack(side="left")

        # Уведомление об OCR (показывается при наличии PDF без Tesseract)
        self.lbl_ocr_hint = ctk.CTkLabel(
            fc, text="", font=("Segoe UI", 11), text_color="#b42309",
            anchor="center", justify="center", wraplength=350)
        self.lbl_ocr_hint.pack(fill="x", padx=4, pady=(0, 2))

        # Папка экспорта — pack для точного выравнивания
        row_out = ctk.CTkFrame(fc, fg_color="transparent")
        row_out.pack(fill="x", pady=4)
        ctk.CTkLabel(row_out, text="Папка экспорта:", font=FONT_LABEL,
                     text_color=FG_LABEL).pack(side="left", padx=(0, 8))
        self.ent_out_dir = ctk.CTkEntry(row_out)
        self.ent_out_dir.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.ent_out_dir.insert(0, self.DEFAULT_OUT_PLACEHOLDER)
        self.bind_edit_actions(self.ent_out_dir)
        ctk.CTkButton(row_out, text="Обзор", command=self.browse_out_dir,
                       **self._btn_kw(width=70)).pack(side="left")

        # Префикс чанков — pack
        row_base = ctk.CTkFrame(fc, fg_color="transparent")
        row_base.pack(fill="x", pady=4)
        ctk.CTkLabel(row_base, text="Префикс чанков:", font=FONT_LABEL,
                     text_color=FG_LABEL).pack(side="left", padx=(0, 8))
        self.ent_base_name = ctk.CTkEntry(row_base)
        self.ent_base_name.pack(side="left", fill="x", expand=True)
        self.ent_base_name.insert(0, "(Опционально)")
        self.bind_edit_actions(self.ent_base_name)

        # — Управление и прогресс —
        lf_act, ac = self._card_section(left_scroll, "Управление и прогресс")
        lf_act.pack(fill="x", pady=(0, 5))

        self.btn_start = ctk.CTkButton(
            ac, text="▶ Начать обработку", command=self.toggle_process,
            corner_radius=10, height=38, font=FONT_BTN_SM,
            fg_color=ACCENT, hover_color=ACCENT_HOV, text_color="white")
        self.btn_start.pack(fill="x", pady=(4, 8))

        self.lbl_progress_file = ctk.CTkLabel(ac, text="Прогресс файла:", font=FONT_LABEL,
                     text_color=FG_LABEL)
        self.lbl_progress_file.pack(anchor="w")
        self.progress_chunk = ctk.CTkProgressBar(ac, height=8, corner_radius=4,
                                                  progress_color=ACCENT,
                                                  fg_color="#e5e7eb")
        self.progress_chunk.pack(fill="x", pady=(2, 6))
        self.progress_chunk.set(0)

        ctk.CTkLabel(ac, text="Общий прогресс конвейера:", font=FONT_LABEL,
                     text_color=FG_LABEL).pack(anchor="w")
        self.progress_total = ctk.CTkProgressBar(ac, height=8, corner_radius=4,
                                                  progress_color=ACCENT,
                                                  fg_color="#e5e7eb")
        self.progress_total.pack(fill="x", pady=(2, 4))
        self.progress_total.set(0)

        # — Параметры обработки —
        lf_sets, sc = self._card_section(left_scroll, "Параметры обработки")
        lf_sets.pack(fill="x", pady=5)
        sc.grid_columnconfigure(0, weight=1)
        sc.grid_columnconfigure(1, weight=1)

        cf = ctk.CTkFrame(sc, fg_color="transparent")
        cf.grid(row=0, column=0, columnspan=2, sticky="ew", pady=2)
        ctk.CTkLabel(cf, text="Размер чанка:", font=FONT_LABEL,
                     text_color=FG_LABEL).pack(side="left", padx=(0, 4))
        self.ent_chunk_size = ctk.CTkEntry(cf, width=80)
        self.ent_chunk_size.pack(side="left", padx=(0, 12))
        self.ent_chunk_size.insert(0, "10000")
        ctk.CTkLabel(cf, text="Перекрытие:", font=FONT_LABEL,
                     text_color=FG_LABEL).pack(side="left", padx=(0, 4))
        self.ent_chunk_overlap = ctk.CTkEntry(cf, width=80)
        self.ent_chunk_overlap.pack(side="left")
        self.ent_chunk_overlap.insert(0, "1500")

        wf = ctk.CTkFrame(sc, fg_color="transparent")
        wf.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)
        ctk.CTkLabel(wf, text="Количество потоков:", font=FONT_LABEL,
                     text_color=FG_LABEL).pack(side="left")
        self.var_workers = ctk.StringVar(value="1")
        ctk.CTkOptionMenu(wf, variable=self.var_workers,
                          values=[str(i) for i in range(1, 9)],
                          width=60, font=FONT_BTN,
                          fg_color=BG_INPUT, button_color=BORDER,
                          button_hover_color=BTN_HOVER,
                          text_color=FG_TITLE,
                          dropdown_fg_color=BG_CARD,
                          dropdown_hover_color=ACCENT,
                          dropdown_text_color=FG_TITLE
                          ).pack(side="left", padx=(6, 0))

        self.var_cleanup = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(sc, text="Очищать временные файлы",
                        variable=self.var_cleanup, font=FONT_BTN,
                        text_color=FG_TITLE, fg_color=BTN_BG,
                        hover_color=BTN_HOVER, checkmark_color=FG_TITLE,
                        border_width=1, border_color=BORDER
                        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

        self.var_skip_llm = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(sc, text="Только нарезка и конверсия",
                        variable=self.var_skip_llm, font=FONT_BTN,
                        text_color=FG_TITLE, fg_color=BTN_BG,
                        hover_color=BTN_HOVER, checkmark_color=FG_TITLE,
                        border_width=1, border_color=BORDER
                        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=4)

        # Формат выходных файлов
        row_fmt = ctk.CTkFrame(sc, fg_color="transparent")
        row_fmt.grid(row=4, column=0, columnspan=2, sticky="ew", pady=4)
        ctk.CTkLabel(row_fmt, text="Формат вывода:", font=FONT_LABEL,
                     text_color=FG_LABEL).pack(side="left", padx=(0, 8))
        self.var_output_format = ctk.StringVar(value="spr")
        ctk.CTkOptionMenu(row_fmt, variable=self.var_output_format,
                          values=["spr", "frontmatter", "markdown"],
                          width=120, font=FONT_BTN,
                          fg_color=BG_INPUT, button_color=BORDER,
                          button_hover_color=BTN_HOVER, text_color=FG_TITLE,
                          dropdown_fg_color=BG_CARD, dropdown_hover_color=ACCENT,
                          dropdown_text_color=FG_TITLE
                          ).pack(side="left")

        # — Провайдер LLM —
        lf_prov, pc = self._card_section(left_scroll, "Настройки провайдера LLM")
        lf_prov.pack(fill="x", pady=(5, 0))
        pc.grid_columnconfigure(1, weight=1)

        for row, (lbl, show) in enumerate([
            ("Модель:", None), ("Base URL:", None), ("API Key:", "*")]):
            ctk.CTkLabel(pc, text=lbl, font=FONT_LABEL, text_color=FG_LABEL
                         ).grid(row=row, column=0, sticky="w", padx=4, pady=4)
            ent = ctk.CTkEntry(pc, show=show or "")
            ent.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            self.bind_edit_actions(ent)
            setattr(self, ["ent_model", "ent_url", "ent_key"][row], ent)

        # — Сохранение —
        lf_save = ctk.CTkFrame(left_scroll, fg_color=BG_CARD, corner_radius=10,
                               border_width=1, border_color=BORDER)
        lf_save.pack(fill="x", pady=5)
        svc = ctk.CTkFrame(lf_save, fg_color="transparent")
        svc.pack(fill="both", expand=True, padx=8, pady=8)
        ctk.CTkButton(svc, text="💾 Сохранить настройки", command=self.save_settings,
                       corner_radius=8, height=32, font=FONT_BTN_SM,
                       fg_color=BTN_BG, hover_color=BTN_HOVER,
                       text_color=BTN_FG
                       ).pack(fill="x", pady=(4, 0))

        # ─── ПРАВАЯ ЧАСТЬ ───────────────────────────────────
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=2)
        right.grid_rowconfigure(1, weight=1)

        # — Системный промпт —
        lf_pr, prc = self._card_section(right, "Системный промпт / System Prompt")
        lf_pr.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        pmf = ctk.CTkFrame(prc, fg_color="transparent")
        pmf.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(pmf, text="Шаблон:", font=FONT_LABEL,
                     text_color=FG_LABEL).pack(side="left", padx=(0, 4))
        self.var_prompt_template = ctk.StringVar(value="")
        self.combo_prompt = ctk.CTkOptionMenu(
            pmf, variable=self.var_prompt_template, values=[""],
            command=self.on_prompt_template_changed,
            width=260, font=FONT_BTN,
            fg_color=BTN_BG, button_color=BORDER,
            button_hover_color=BTN_HOVER, text_color=BTN_FG,
            dropdown_fg_color=BG_CARD, dropdown_hover_color=ACCENT,
            dropdown_text_color=FG_TITLE)
        self.combo_prompt.pack(side="left", padx=(0, 6))

        ctk.CTkButton(pmf, text="➕ Сохранить как...", command=self.save_prompt_as_new,
                       **self._btn_kw(width=140)).pack(side="left", padx=(0, 4))
        ctk.CTkButton(pmf, text="🗑 Удалить", command=self.delete_prompt,
                       **self._btn_kw(width=100)).pack(side="left", padx=(0, 4))
        ctk.CTkButton(pmf, text="Сброс", command=self.reset_prompt,
                       **self._btn_kw(width=80)).pack(side="right")

        self.txt_prompt = ctk.CTkTextbox(prc, font=FONT_MONO, wrap="word",
                                          fg_color=BG_INPUT, text_color=FG_TITLE,
                                          border_width=1, border_color=BORDER,
                                          corner_radius=6)
        self.txt_prompt.pack(fill="both", expand=True)
        self.bind_edit_actions(self.txt_prompt)

        # — Лог —
        lf_log, lgc = self._card_section(right, "Лог событий / Event Log")
        lf_log.grid(row=1, column=0, sticky="nsew", pady=(5, 0))

        self.txt_logs = ctk.CTkTextbox(lgc, font=FONT_MONO, wrap="word",
                                        fg_color="#1e293b", text_color="#94a3b8",
                                        border_width=0, corner_radius=6)
        self.txt_logs.pack(fill="both", expand=True)
        self.bind_edit_actions(self.txt_logs)

    # ──────────────────────────────────────────────────────────
    #  Логирование
    # ──────────────────────────────────────────────────────────
    def log(self, message):
        ts = datetime.now().strftime("[%H:%M:%S]")
        self.root.after(0, self._log_safe, ts, message)

    def _log_safe(self, ts, msg):
        self.txt_logs.insert("end", f"{ts} {msg}\n")
        self.txt_logs.see("end")

    # ──────────────────────────────────────────────────────────
    #  Работа с файлами
    # ──────────────────────────────────────────────────────────
    def browse_src_file(self):
        filetypes = [
            ("Поддерживаемые файлы", "*.txt *.md *.docx *.doc *.pdf"),
            ("Документы Word", "*.docx *.doc"),
            ("PDF документы", "*.pdf"),
            ("Текстовые файлы", "*.txt *.md"),
            ("Все файлы", "*.*")]
        filenames = filedialog.askopenfilenames(filetypes=filetypes)
        if filenames:
            existing = set(self.file_paths)
            added = 0
            for f in filenames:
                if f not in existing:
                    self.file_paths.append(f)
                    self.file_list.insert(f)
                    added += 1
            first = os.path.basename(self.file_paths[0]) if self.file_paths else ""
            self.ent_base_name.delete(0, "end")
            self.ent_base_name.insert(0, f"{os.path.splitext(first)[0]}_chunk")
            self._update_ocr_hint()
            self.log(f"📚 Добавлено: {added}, уже было: {len(filenames) - added}, "
                     f"всего в очереди: {self.file_list.size()}")

    def remove_selected_files(self):
        for i in reversed(self.file_list.curselection()):
            self.file_list.delete(i)
            del self.file_paths[i]
        self._update_ocr_hint()
        self.log(f"✖ Файлов в очереди: {self.file_list.size()}")

    def clear_files(self):
        self.file_list.clear()
        self.file_paths.clear()
        self._update_ocr_hint()
        self.log("🗑 Список файлов очищен.")

    def _update_ocr_hint(self):
        """Показывает/скрывает уведомление о необходимости Tesseract для PDF."""
        has_pdf = any(p.lower().endswith(".pdf") for p in self.file_paths)
        if has_pdf and not etl_pipeline.OCR_AVAILABLE:
            self.lbl_ocr_hint.configure(
                text="ℹ️ Для распознавания сканированных PDF установите Tesseract-OCR")
        else:
            self.lbl_ocr_hint.configure(text="")

    def _on_file_select(self, idx):
        """Обработчик клика по файлу в списке — обновляет прогресс-бар."""
        self._watched_file_idx = idx
        file_path = self.file_paths[idx] if idx < len(self.file_paths) else None
        file_name = os.path.basename(file_path) if file_path else ""
        self.lbl_progress_file.configure(text=f"Прогресс: {file_name}")
        pct = self.file_progress.get(file_path, 0)
        self.progress_chunk.set(pct / 100)

    def browse_out_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.ent_out_dir.delete(0, "end")
            self.ent_out_dir.insert(0, directory)
            self.log(f"Выбрана папка сохранения: {directory}")

    # ──────────────────────────────────────────────────────────
    #  Промпты
    # ──────────────────────────────────────────────────────────
    def on_prompt_template_changed(self, selected_value):
        if selected_value in self.prompts_library:
            self.txt_prompt.delete("1.0", "end")
            self.txt_prompt.insert("end", self.prompts_library[selected_value])
            self.log(f"🔄 Переключено на промпт: '{selected_value}'")

    def save_prompt_as_new(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Новый шаблон")
        dialog.geometry("380x140")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(fg_color=BG_MAIN)

        ctk.CTkLabel(dialog, text="Введите название для этого промпта:",
                     font=FONT_LABEL, text_color=FG_LABEL
                     ).pack(anchor="w", padx=12, pady=(14, 4))
        ent_name = ctk.CTkEntry(dialog, placeholder_text="Имя шаблона…")
        ent_name.pack(fill="x", padx=12, pady=(0, 8))
        ent_name.focus_set()

        def confirm():
            name = ent_name.get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Имя не может быть пустым!", parent=dialog)
                return
            self.prompts_library[name] = self.txt_prompt.get("1.0", "end").strip()
            self.combo_prompt.configure(values=list(self.prompts_library.keys()))
            self.combo_prompt.set(name)
            self.log(f"➕ Добавлен новый шаблон промпта: '{name}'")
            dialog.destroy()
            self.save_settings()

        ctk.CTkButton(dialog, text="Сохранить", command=confirm,
                       corner_radius=8, height=32, font=FONT_BTN_SM,
                       fg_color=ACCENT, hover_color=ACCENT_HOV,
                       text_color="white").pack(anchor="e", padx=12, pady=(0, 10))

    def delete_prompt(self):
        """Удаляет текущий выбранный промпт из библиотеки."""
        name = self.var_prompt_template.get()
        if not name or name not in self.prompts_library:
            messagebox.showwarning("Внимание", "Выберите промпт для удаления из списка шаблонов.")
            return
        if len(self.prompts_library) <= 1:
            messagebox.showwarning("Внимание", "Нельзя удалить последний промпт в библиотеке.")
            return
        if not messagebox.askyesno("Подтверждение", f"Удалить промпт «{name}»?"):
            return
        del self.prompts_library[name]
        remaining = list(self.prompts_library.keys())
        self.combo_prompt.configure(values=remaining)
        self.combo_prompt.set(remaining[0])
        self.on_prompt_template_changed(remaining[0])
        self.log(f"🗑 Удалён промпт: «{name}»")
        self.save_settings()

    def reset_prompt(self):
        self.txt_prompt.delete("1.0", "end")
        self.txt_prompt.insert("end", self.DEFAULT_PROMPT)
        self.log("Промпт сброшен к стандартному SPR шаблону.")

    # ──────────────────────────────────────────────────────────
    #  Настройки
    # ──────────────────────────────────────────────────────────
    def save_settings(self):
        try:
            name = self.var_prompt_template.get() or "Дефолтный SPR"
            self.prompts_library[name] = self.txt_prompt.get("1.0", "end").strip()
            try:
                c_size = int(self.ent_chunk_size.get().strip())
                c_overlap = int(self.ent_chunk_overlap.get().strip())
            except ValueError:
                messagebox.showerror("Ошибка",
                                     "Размер чанка и перекрытие должны быть целыми числами!")
                return
            config_manager.save_config(
                model=self.ent_model.get(),
                base_url=self.ent_url.get(),
                api_key=self.ent_key.get(),
                chunk_size=c_size, chunk_overlap=c_overlap,
                max_workers=int(self.var_workers.get()),
                output_format=self.var_output_format.get(),
                prompts_dict=self.prompts_library,
                current_prompt_name=name)
            self.log("💾 Все настройки приложения и библиотека промптов успешно сохранены.")
            messagebox.showinfo("Успех", "Все настройки сохранены!")
        except Exception as e:
            self.log(f"❌ Не удалось сохранить настройки: {e}")
            messagebox.showerror("Ошибка", str(e))

    def load_settings(self):
        cfg = config_manager.load_config()
        self.ent_model.delete(0, "end")
        self.ent_url.delete(0, "end")
        self.ent_key.delete(0, "end")

        if cfg:
            self.ent_model.insert(0, cfg.get("model", "llama3"))
            self.ent_url.insert(0, cfg.get("base_url", "http://localhost:11434/v1"))
            self.ent_key.insert(0, cfg.get("api_key", "ollama"))
            self.var_workers.set(str(cfg.get("max_workers", 1)))
            self.ent_chunk_size.delete(0, "end")
            self.ent_chunk_size.insert(0, str(cfg.get("chunk_size", 10000)))
            self.ent_chunk_overlap.delete(0, "end")
            self.ent_chunk_overlap.insert(0, str(cfg.get("chunk_overlap", 1500)))
            self.var_output_format.set(cfg.get("output_format", "spr"))
            self.prompts_library = cfg.get("prompts", {})
            if not self.prompts_library:
                self.prompts_library = {"Дефолтный SPR": self.DEFAULT_PROMPT}
            active = cfg.get("current_prompt_name")
            if not active or active not in self.prompts_library:
                active = list(self.prompts_library.keys())[0]
            self.combo_prompt.configure(values=list(self.prompts_library.keys()))
            self.combo_prompt.set(active)
            self.txt_prompt.delete("1.0", "end")
            self.txt_prompt.insert("end", self.prompts_library[active])
            self.log(f"📂 Конфигурация успешно загружена из: {config_manager.CONFIG_FILE}")
        else:
            self.ent_model.insert(0, "llama3")
            self.ent_url.insert(0, "http://localhost:11434/v1")
            self.ent_key.insert(0, "ollama")
            self.prompts_library = {"Дефолтный SPR": self.DEFAULT_PROMPT}
            self.combo_prompt.configure(values=list(self.prompts_library.keys()))
            self.combo_prompt.set("Дефолтный SPR")
            self.txt_prompt.insert("end", self.DEFAULT_PROMPT)
            self.log(f"ℹ️ Конфиг не найден в {BASE_DIR}. Загружены дефолтные параметры.")

    # ──────────────────────────────────────────────────────────
    #  Конвейер
    # ──────────────────────────────────────────────────────────
    def toggle_process(self):
        if self.is_processing:
            self.stop_requested = True
            self.log("Запрошена остановка конвейера... Ожидание завершения чанка.")
            self.btn_start.configure(state="disabled")
        else:
            self.start_pipeline()

    def start_pipeline(self):
        if not self.file_paths:
            messagebox.showerror("Ошибка", "Добавьте хотя бы один файл в список!")
            return
        validated = []
        for src in self.file_paths:
            if not os.path.isabs(src):
                src = os.path.abspath(os.path.join(BASE_DIR, src))
            if os.path.exists(src):
                validated.append(src)
            else:
                self.log(f"⚠️ Файл не найден и пропущен: {src}")
        if not validated:
            messagebox.showerror("Ошибка", "Ни один из указанных файлов не найден на диске!")
            return

        out = self.ent_out_dir.get().strip()
        is_default = (out == self.DEFAULT_OUT_PLACEHOLDER or not out)
        cfg = {
            "is_default_out": is_default, "user_out_dir": out,
            "base_name": self.ent_base_name.get().strip() or "chunk",
            "model": self.ent_model.get(), "url": self.ent_url.get(),
            "key": self.ent_key.get(),
            "chunk_size": int(self.ent_chunk_size.get().strip() or 10000),
            "chunk_overlap": int(self.ent_chunk_overlap.get().strip() or 1500),
            "max_workers": int(self.var_workers.get()),
            "prompt": self.txt_prompt.get("1.0", "end").strip(),
            "cleanup": self.var_cleanup.get(),
            "skip_llm": self.var_skip_llm.get(),
            "output_format": self.var_output_format.get()}
        self.is_processing = True
        self.stop_requested = False
        self.file_progress.clear()
        self.btn_start.configure(text="🛑 Остановить обработку")
        threading.Thread(target=self._worker, args=(validated, cfg), daemon=True).start()

    def _worker(self, files, cfg):
        try:
            ok = etl_pipeline.process_batch(
                file_list=files, global_cfg=cfg,
                progress_callback=self.update_progress,
                log_callback=self.log,
                stop_check_callback=lambda: self.stop_requested,
                max_workers=cfg["max_workers"])
            if ok:
                self.log("🎉 Пакетная обработка всех документов успешно завершена!")
                self.root.after(0, lambda: messagebox.showinfo(
                    "Успех", "Все файлы из пакета обработаны!"))
            else:
                self.log("🛑 Обработка пакета была остановлена пользователем.")
        except Exception as e:
            err = str(e)
            self.log(f"💥 Критическая ошибка пакетного конвейера: {err}")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", err))
        finally:
            self.root.after(0, self._reset_ui)

    def _reset_ui(self):
        self.is_processing = False
        self.btn_start.configure(text="▶ Начать обработку", state="normal")
        self.progress_chunk.set(0)
        self.progress_total.set(0)
        self.file_progress.clear()

    def update_progress(self, chunk_val, total_val, file_idx=None):
        self.root.after(0, self._update_progress, chunk_val, total_val, file_idx)

    def _update_progress(self, chunk_val, total_val, file_idx=None):
        # Сохраняем прогресс конкретного файла
        if file_idx is not None and file_idx < len(self.file_paths):
            self.file_progress[self.file_paths[file_idx]] = chunk_val
            # Обновляем прогресс-бар если это отслеживаемый файл
            if file_idx == self._watched_file_idx:
                self.progress_chunk.set(chunk_val / 100)
        if total_val is not None:
            self.progress_total.set(total_val / 100)


# ═══════════════════════════════════════════════════════════════
# if __name__ == "__main__":
#     ctk.set_appearance_mode("light")
#     ctk.set_default_color_theme("blue")
#     root = ctk.CTk()
#     app = SimpleETLApp(root)
#     root.mainloop()
