import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
HERE = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
if not getattr(sys, 'frozen', False):
    # Local development dependencies, also when started from a login shortcut.
    import site
    site.addsitedir(str(HERE / 'builddeps'))
    if str(HERE / 'vendor') not in sys.path:
        sys.path.insert(0, str(HERE / 'vendor'))
if getattr(sys, 'frozen', False):
    os.environ['PATH'] = str(HERE / 'vapoursynth') + os.pathsep + str(HERE) + os.pathsep + os.environ.get('PATH', '')
    for directory in (HERE, HERE / 'vapoursynth', HERE / 'upscale_ncnn_py'):
        if directory.exists():
            os.add_dll_directory(str(directory))
if '--apply-update' in sys.argv:
    from app_updates import apply
    apply(sys.argv[sys.argv.index('--apply-update')+1])
    sys.exit(0)
if '--autostart' in sys.argv:
    from preferences import run_startup
    run_startup()
    sys.exit(0)
if '--describe' in sys.argv or '--api' in sys.argv:
    from automation import command_line
    command_line()
    sys.exit(0)
if '--mcp' in sys.argv:
    from mcp_server import serve
    serve()
    sys.exit(0)
if '--worker' in sys.argv:
    from engine import worker
    i = sys.argv.index('--worker')
    try:
        worker(sys.argv[i + 1], sys.argv[i + 2])
    except BaseException:
        sys.exit(1)
    sys.exit(0)
font = HERE / 'fonts/Inter.ttf'
if font.is_file():
    ctypes.windll.gdi32.AddFontResourceExW(str(font), 16, 0)
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from PIL import Image
import psutil
import sqlite3
from contextlib import closing
from i18n import translate, TOOLTIPS, HELP_EN, HELP_DE, OCR_PURPOSE
from review import review_prompt
from ui_icons import icon
import preferences
import archive_layout
from app_version import VERSION
ctk.set_appearance_mode('dark')
BG = '#111820'
PANEL = '#19242e'
EDGE = '#2d3b48'
TEXT = '#ecf2f5'
MUTED = '#9eafbc'
ACCENT = '#69d8bd'

class Tooltip:

    def __init__(self, widget, text):
        self.widget, self.text = (widget, text)
        self.pending = None
        self.window = None

        def bind_children(child):
            try:
                child.bind('<Enter>', self.enter, add='+')
                child.bind('<Leave>', self.leave, add='+')
                child.bind('<ButtonPress>', self.leave, add='+')
            except NotImplementedError:
                pass
            for nested in child.winfo_children():
                bind_children(nested)
        bind_children(widget)

    def enter(self, event=None):
        if self.pending:
            self.widget.after_cancel(self.pending)
        self.pending = self.widget.after(500, self.show)

    def leave(self, event=None):
        if self.pending:
            self.widget.after_cancel(self.pending)
            self.pending = None
        if self.window:
            self.window.destroy()
            self.window = None

    def show(self):
        self.pending = None
        if self.window or not self.widget.winfo_exists():
            return
        self.window = ctk.CTkToplevel(self.widget)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        label = ctk.CTkLabel(self.window, text=self.text, wraplength=360, justify='left', font=('Inter', 12), text_color=TEXT, fg_color=EDGE, corner_radius=7)
        label.pack(ipadx=12, ipady=9)
        self.window.update_idletasks()
        x = min(self.widget.winfo_pointerx() + 12, self.widget.winfo_screenwidth() - self.window.winfo_width() - 15)
        y = min(self.widget.winfo_pointery() + 20, self.widget.winfo_screenheight() - self.window.winfo_height() - 15)
        self.window.geometry(f'+{max(0, x)}+{max(0, y)}')

class Studio(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.saved_settings = preferences.load()
        if not isinstance(self.saved_settings, dict):
            self.saved_settings = {}
        self.language = self.saved_settings.get('language', 'de')
        self.title(self.t('VHS Studio · Familienaufnahmen aufbereiten'))
        self.geometry('1180x940')
        self.minsize(1080, 900)
        self.configure(fg_color=BG)
        self.proc = None
        self.plan = []
        self.run_config = None
        self.offset = 0
        self.events = None
        self.temp = None
        self.scanning = False
        self.publishing = False
        self.workspaces = []
        self.jobs_done = 0
        self.finished = False
        self.last_stamps_refresh = 0
        self._build()
        self.restore_settings(self.saved_settings)
        self.sync_controls()
        from automation import register_instance
        register_instance()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(150, self.poll)
        self.after(2000, self.autosave)
        self.update_result = None
        self.update_info = None
        self.after(2500, self.start_update_check)
        if '--screenshot-test' in sys.argv:
            self.after(1500, self.test_ready)

    def t(self, text):
        return translate(self.language, text)

    def label(self, parent, text, size=14, color=TEXT, weight='normal', **kwargs):
        return ctk.CTkLabel(parent, text=self.t(text), text_color=color, font=ctk.CTkFont(family='Inter', size=size, weight=weight), **kwargs)

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=30, pady=(23, 17))
        header.grid_columnconfigure(1, weight=1)
        cassette = tk.Canvas(header, width=51, height=39, bg=BG, highlightthickness=0)
        cassette.grid(row=0, column=0, rowspan=2, padx=(0, 15))
        cassette.create_rectangle(2, 2, 49, 36, outline=ACCENT, width=2)
        cassette.create_rectangle(8, 9, 43, 24, outline=ACCENT)
        for x in (17, 34):
            cassette.create_oval(x - 5, 12, x + 5, 22, outline=ACCENT, width=2)
        self.label(header, 'VHS STUDIO', 23, weight='bold').grid(row=0, column=1, sticky='w')
        self.label(header, self.t('Familienaufnahmen erhalten und aufbereiten'), 13, MUTED).grid(row=1, column=1, sticky='w')
        actions = ctk.CTkFrame(header, fg_color='transparent')
        actions.grid(row=0, column=2, rowspan=3, sticky='e')
        self.folder_icon, self.ai_icon = icon('folder'), icon('ai')
        ctk.CTkButton(actions, text=self.t('Ausgabe öffnen'), image=self.folder_icon, width=145, height=34, fg_color=PANEL, hover_color=EDGE, command=self.open_output).grid(row=0, column=0, padx=(0, 8), pady=(0, 8))
        self.helpbutton = ctk.CTkButton(actions, text='ⓘ  ' + self.t('So funktioniert’s'), width=145, height=34, fg_color=PANEL, hover_color=EDGE, command=self.help)
        self.helpbutton.grid(row=1, column=0, padx=(0, 8))
        flag_image = Image.new('RGB', (28, 18))
        for y in range(18):
            for x in range(28):
                if self.language == 'de':
                    color = ('#171717', '#dc3030', '#f1c44b')[min(2, y // 6)]
                else:
                    color = '#254780'
                    if abs(y - x * 18 / 28) < 2 or abs(y - (18 - x * 18 / 28)) < 2 or 11 <= x <= 16 or (6 <= y <= 11):
                        color = '#f5f5f5'
                    if 12 <= x <= 15 or 7 <= y <= 10:
                        color = '#d72f43'
                flag_image.putpixel((x, y), tuple(bytes.fromhex(color[1:])))
        self.flag = ctk.CTkImage(light_image=flag_image, dark_image=flag_image, size=(28, 18))
        self.language_button = ctk.CTkButton(actions, text='DE' if self.language == 'de' else 'EN', image=self.flag, width=105, height=34, fg_color=PANEL, hover_color=EDGE, command=self.switch_language)
        self.language_button.grid(row=0, column=1, pady=(0, 8))
        paths = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        paths.grid(row=1, column=0, sticky='ew', padx=30, pady=(0, 16))
        paths.grid_columnconfigure(1, weight=1)
        self.label(paths, self.t('Aufnahmen'), 14, weight='bold').grid(row=0, column=0, padx=18, pady=(16, 8), sticky='w')
        self.source = ctk.CTkEntry(paths, height=37, placeholder_text=self.t('Ordner mit digitalisierten VHS-Aufnahmen auswählen'), fg_color=BG, border_color=EDGE)
        self.source.grid(row=0, column=1, sticky='ew', pady=(16, 8))
        self.source.bind('<KeyRelease>', lambda e: self.invalidate())
        self.source_button = ctk.CTkButton(paths, text=self.t('Ordner wählen'), width=125, height=37, fg_color=EDGE, hover_color='#3d5262', command=lambda: self.browse(self.source))
        self.source_button.grid(row=0, column=2, padx=16, pady=(16, 8))
        self.label(paths, self.t('Ablage'), 14, weight='bold').grid(row=1, column=0, padx=18, pady=6, sticky='w')
        self.mode = ctk.CTkOptionMenu(paths, values=[self.t('In Ausgabeordner exportieren'), self.t('Familienarchiv fortführen')], width=260, height=33, fg_color=EDGE, button_color=EDGE, command=self.mode_changed)
        self.mode.grid(row=1, column=1, sticky='w', pady=6)
        self.label(paths, self.t('Ziel'), 14, weight='bold').grid(row=2, column=0, padx=18, pady=(6, 12), sticky='w')
        self.output = ctk.CTkEntry(paths, height=37, placeholder_text=self.t('Ausgabeordner'), fg_color=BG, border_color=EDGE)
        self.output.grid(row=2, column=1, sticky='ew', pady=(6, 12))
        self.output.bind('<KeyRelease>', lambda e: self.invalidate())
        self.output_button = ctk.CTkButton(paths, text=self.t('Ordner wählen'), width=125, height=37, fg_color=EDGE, hover_color='#3d5262', command=lambda: self.browse(self.output))
        self.output_button.grid(row=2, column=2, padx=16, pady=(6, 12))
        self.recursive = ctk.CTkCheckBox(paths, text=self.t('Unterordner einbeziehen'), font=('Inter', 12), checkbox_width=17, checkbox_height=17, fg_color=ACCENT, checkmark_color=BG, command=self.invalidate)
        self.recursive.select()
        self.recursive.grid(row=3, column=1, sticky='w', pady=(0, 15))
        self.mode_hint = self.label(paths, self.t('Geprüfte MP4s werden im Ausgabeordner abgelegt.'), 12, MUTED)
        self.mode_hint.grid(row=4, column=1, columnspan=2, sticky='w', pady=(0, 12))
        self.autostart_button = ctk.CTkButton(paths, text=self.t('Autostart einrichten'), width=160, height=30, fg_color=EDGE, command=self.show_autostart)
        self.autostart_button.grid(row=3, column=2, sticky='e', padx=16, pady=(0, 8))
        controls = ctk.CTkFrame(self, fg_color='transparent')
        controls.grid(row=2, column=0, sticky='ew', padx=30, pady=(0, 16))
        for col in range(3):
            controls.grid_columnconfigure(col, weight=1, uniform='cards')
        cards = []
        for i in range(3):
            frame = ctk.CTkFrame(controls, fg_color=PANEL, corner_radius=12)
            frame.grid(row=0, column=i, sticky='nsew', padx=(0, 12) if i < 2 else 0)
            frame.grid_columnconfigure(0, weight=1)
            cards.append(frame)
        self.deint = ctk.CTkSwitch(cards[0], text=self.t('Halbbilder korrigieren'), font=('Inter', 15, 'bold'), progress_color=ACCENT, command=self.invalidate)
        self.deint.select()
        self.deint.grid(row=0, column=0, padx=17, pady=(18, 8), sticky='w')
        self.label(cards[0], self.t('Ruhigere Bewegung, weniger Kammstreifen'), 12, MUTED).grid(row=1, column=0, sticky='w', padx=17)
        self.method = ctk.CTkSegmentedButton(cards[0], values=['QTGMC', 'BWDIF'], selected_color='#356e64', command=lambda _: self.invalidate())
        self.method.set('QTGMC')
        self.method.grid(row=2, column=0, sticky='ew', padx=17, pady=12)
        self.replace = ctk.CTkCheckBox(cards[0], text=self.t('Alte BWDIF-Fassungen auf QTGMC erneuern'), font=('Inter', 11), checkbox_width=17, checkbox_height=17, fg_color=ACCENT, checkmark_color=BG, command=self.invalidate)
        self.replace.grid(row=3, column=0, sticky='w', padx=17, pady=(0, 17))
        self.upscale = ctk.CTkSwitch(cards[1], text=self.t('Details vergrößern'), font=('Inter', 15, 'bold'), progress_color=ACCENT, command=self.invalidate)
        self.upscale.grid(row=0, column=0, padx=17, pady=(18, 8), sticky='w')
        self.label(cards[1], self.t('OpenProteus · zweifache Bildgröße'), 12, MUTED).grid(row=1, column=0, sticky='w', padx=17)
        self.label(cards[1], self.t('Modell nachladen · nichtkommerziell'), 13).grid(row=2, column=0, padx=17, pady=14, sticky='w')
        self.label(cards[1], self.t('Benötigt eine Vulkan-fähige Grafikkarte.\nVHS wird vorab deinterlaced.'), 12, MUTED, justify='left').grid(row=3, column=0, padx=17, pady=(0, 15), sticky='w')
        self.ocr = ctk.CTkSwitch(cards[2], text=self.t('Datumsstempel lesen'), font=('Inter', 15, 'bold'), progress_color=ACCENT, command=self.invalidate)
        self.ocr.grid(row=0, column=0, padx=17, pady=(18, 8), sticky='w')
        self.ocr_hint = self.label(cards[2], self.t('Mehrere Aufnahmetage auf einer Kassette?\nHinweise für eine spätere Trennung finden.'), 12, MUTED, justify='left')
        self.ocr_hint.grid(row=1, column=0, sticky='w', padx=17)
        self.rate_label = self.label(cards[2], 'Scan-Raster · 1 Bild/s', 13)
        self.rate_label.grid(row=2, column=0, padx=17, pady=(12, 5), sticky='w')
        self.rate = ctk.CTkSlider(cards[2], from_=0, to=4, number_of_steps=4, progress_color=ACCENT, button_color=ACCENT, command=self.rate_changed)
        self.rate.set(2)
        self.rate.grid(row=3, column=0, sticky='ew', padx=17, pady=(0, 8))
        self.label(cards[2], self.t('Nur Fundstellen · kein automatischer Schnitt.'), 11, MUTED).grid(row=4, column=0, padx=17, pady=(0, 12), sticky='w')
        center = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        center.grid(row=3, column=0, sticky='nsew', padx=30)
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(1, weight=1)
        bar = ctk.CTkFrame(center, fg_color='transparent')
        bar.grid(row=0, column=0, sticky='ew', padx=17, pady=(12, 7))
        bar.grid_columnconfigure(0, weight=1)
        self.queue_title = self.label(bar, self.t('Arbeitsbereich'), 15, weight='bold')
        self.queue_title.grid(row=0, column=0, sticky='w')
        self.label(bar, self.t('Dateien pro Lauf'), 12, MUTED).grid(row=0, column=1, padx=(10, 8))
        self.limit = ctk.CTkEntry(bar, width=56, height=30, fg_color=BG, border_color=EDGE)
        self.limit.insert(0, '2')
        self.limit.grid(row=0, column=2)
        self.limit.bind('<KeyRelease>', lambda e: self.invalidate())
        self.label(bar, self.t('0 = alle'), 11, MUTED).grid(row=0, column=3, padx=(7, 15))
        self.cpu_names = ['Schonend', 'Ausgewogen', 'Volle Leistung', 'Hintergrund / Spielen']
        self.cpu = ctk.CTkOptionMenu(bar, values=[self.t(x) for x in self.cpu_names], width=190, height=30, fg_color=EDGE, button_color=EDGE, command=lambda _: self.invalidate())
        self.cpu.set(self.t('Schonend'))
        self.label(bar,self.t('Ressourcen'),12,MUTED).grid(row=0,column=4,padx=(0,8))
        self.cpu.grid(row=0, column=5)
        self.tabs = ctk.CTkTabview(center, fg_color=BG, anchor='nw',
            segmented_button_fg_color=PANEL, segmented_button_unselected_color=PANEL,
            segmented_button_unselected_hover_color=EDGE,
            segmented_button_selected_color='#315a52',
            segmented_button_selected_hover_color='#3b7065',
            text_color=TEXT, corner_radius=9, height=135)
        self.tabs._segmented_button.configure(font=('Inter', 13, 'bold'), height=36, corner_radius=7, border_width=5, dynamic_resizing=False)
        self.tabs.grid(row=1, column=0, sticky='nsew', padx=14, pady=(0, 13))
        queue_tab = self.tabs.add(self.t('Dateien'))
        log_tab = self.tabs.add(self.t('Protokoll'))
        stamps = self.tabs.add(self.t('Datumsfunde'))
        self.tabs._segmented_button.grid_configure(sticky='ew')
        self.tabs.configure(command=lambda: self.load_stamps(notify=False))
        stamps.grid_columnconfigure(0, weight=1)
        stamps.grid_rowconfigure(0, weight=1)
        queue_tab.grid_columnconfigure(0, weight=1)
        queue_tab.grid_rowconfigure(0, weight=1)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('VHS.Treeview', background=BG, foreground=TEXT, fieldbackground=BG, borderwidth=0, bordercolor=EDGE, lightcolor=EDGE, darkcolor=EDGE, relief='flat', rowheight=31, font=('Inter', 11))
        style.layout('VHS.Treeview', [('Treeview.treearea', {'sticky':'nswe'})])
        style.configure('VHS.Treeview.Heading', background=PANEL, foreground=MUTED, font=('Inter', 10), relief='flat')
        style.map('VHS.Treeview', background=[('selected', '#2e574f')], foreground=[('selected', TEXT)])
        self.tree = ttk.Treeview(queue_tab, columns=('name', 'length', 'action', 'status'), show='headings', style='VHS.Treeview', height=4)
        for key, title, width in [('name', self.t('Aufnahme'), 310), ('length', self.t('Dauer'), 80), ('action', self.t('Bearbeitung'), 380), ('status', 'Status', 120)]:
            self.tree.heading(key, text=title, anchor='w')
            self.tree.column(key, width=width, minwidth=65, stretch=key in ('name', 'action'))
        self.tree.grid(row=0, column=0, sticky='nsew')
        self.empty_queue=self.label(queue_tab,self.t('Noch keine Dateien geprüft.\nQuelle wählen und »Dateien prüfen« starten.'),13,MUTED,justify='center')
        self.empty_queue.place(relx=.5,rely=.55,anchor='center')
        self.stamp_rows = {}
        self.stamps = ttk.Treeview(stamps, columns=('name', 'time', 'date', 'confirmed', 'boundary', 'review', 'reviewer'), show='headings', style='VHS.Treeview', height=4)
        for key, title, width in [('name', self.t('Aufnahme'), 230), ('time', 'Position', 80), ('date', self.t('OCR-Datum'), 100), ('confirmed', self.t('Geprüftes Datum'), 110), ('boundary', self.t('Grenze (s)'), 90), ('review', self.t('Prüfstatus'), 100), ('reviewer', self.t('Prüfer / Modell'), 200)]:
            self.stamps.heading(key, text=title, anchor='w')
            self.stamps.column(key, width=width, minwidth=65, stretch=key in ('name', 'reviewer'))
        self.stamps.tag_configure('verified',foreground=ACCENT)
        self.stamps.tag_configure('corrected',foreground=ACCENT)
        self.stamps.tag_configure('uncertain',foreground='#e4bc77')
        self.stamps.tag_configure('rejected',foreground=MUTED)
        self.stamps.bind('<Double-1>',lambda e:self.show_finding())
        self.stamps.bind('<Return>',lambda e:self.show_finding())
        self.stamps.grid(row=0, column=0, sticky='nsew')
        self.empty_stamps=self.label(stamps,self.t('Noch keine Datumsfunde.\nOCR aktivieren und einen Lauf starten.'),13,MUTED,justify='center')
        self.empty_stamps.place(relx=.5,rely=.4,anchor='center')
        stamp_scroll = ctk.CTkScrollbar(stamps, command=self.stamps.yview)
        stamp_scroll.grid(row=0, column=1, sticky='ns')
        self.stamps.configure(yscrollcommand=stamp_scroll.set)
        exportbar = ctk.CTkFrame(stamps, fg_color='transparent')
        exportbar.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(9, 0))
        exportbar.grid_columnconfigure(0, weight=1)
        self.copy_notice = self.label(exportbar, self.t('Doppelklick: Prüfdetails · Prüferangaben sind Selbstauskünfte.'), 11, MUTED)
        self.copy_notice.grid(row=0, column=0, sticky='w')
        self.copy_data_button = ctk.CTkButton(exportbar, text=self.t('Funddaten kopieren'), width=145, height=30, fg_color=EDGE, command=lambda: self.copy_ocr(False))
        self.copy_data_button.grid(row=0, column=1, padx=(8, 8))
        self.copy_prompt_button = ctk.CTkButton(exportbar, text=self.t('KI-Prüfauftrag kopieren'), width=175, height=30, fg_color=EDGE, command=lambda: self.copy_ocr(True))
        self.copy_prompt_button.grid(row=0, column=2)
        scroll = ctk.CTkScrollbar(queue_tab, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=scroll.set)
        self.log = ctk.CTkTextbox(log_tab, fg_color=BG, text_color=MUTED, font=('Consolas', 11), wrap='word')
        self.log.pack(fill='both', expand=True)
        self.log.configure(state='disabled')
        footer = ctk.CTkFrame(self, fg_color='transparent')
        footer.grid(row=4, column=0, sticky='ew', padx=30, pady=(15, 20))
        footer.grid_columnconfigure(0, weight=1)
        self.status = self.label(footer, self.t('Quelle wählen und Dateien prüfen.'), 14)
        self.status.grid(row=0, column=0, sticky='w')
        self.detail = self.label(footer, self.t('QTGMC und FFmpeg sind enthalten. Ergebnisse werden vor der Ablage geprüft.'), 11, MUTED)
        self.detail.grid(row=1, column=0, sticky='w', pady=(3, 8))
        self.progress = ctk.CTkProgressBar(footer, height=6, progress_color=ACCENT, fg_color=EDGE)
        self.progress.set(0)
        self.progress.grid(row=2, column=0, sticky='ew', padx=(0, 18))
        self.notifications=ctk.CTkCheckBox(footer,text=self.t('Windows-Benachrichtigungen'),font=('Inter',11),
            checkbox_width=15,checkbox_height=15,fg_color=ACCENT,checkmark_color=BG,command=self.save_settings)
        self.notifications.select()
        self.notifications.grid(row=3,column=0,sticky='w',pady=(9,0))
        buttons = ctk.CTkFrame(footer, fg_color='transparent')
        buttons.grid(row=0, column=1, rowspan=3, sticky='e')
        self.scan_button = ctk.CTkButton(buttons, text=self.t('Dateien prüfen'), width=135, height=42, fg_color=EDGE, hover_color='#3d5262', command=self.scan)
        self.scan_button.grid(row=0, column=0, padx=(0, 9))
        self.start_button = ctk.CTkButton(buttons, text=self.t('Restaurierung starten'), width=174, height=42, fg_color=EDGE, hover_color='#87e3ce', text_color=BG, text_color_disabled=MUTED, font=('Inter', 13, 'bold'), state='disabled', command=self.start)
        self.start_button.grid(row=0, column=1)
        self.stop_button = ctk.CTkButton(buttons, text=self.t('Abbrechen'), width=100, height=30, fg_color='transparent', text_color=MUTED, hover_color=EDGE, command=self.stop, state='disabled')
        self.stop_button.grid(row=1, column=1, sticky='e', pady=(5, 0))
        self.options = [self.source, self.output, self.mode, self.source_button, self.output_button, self.deint, self.method, self.replace, self.upscale, self.ocr, self.recursive, self.limit, self.cpu, self.rate, self.language_button, self.autostart_button,self.notifications]
        self.version_label = self.label(header, f'v{VERSION} · MIT', 11, MUTED)
        self.version_label.grid(row=2, column=1, sticky='w', pady=(3, 0))
        self.mcp_button = ctk.CTkButton(actions, text='KI / MCP' if self.language == 'de' else 'AI / MCP', image=self.ai_icon, width=105, height=34, fg_color=PANEL, hover_color=EDGE, command=self.show_mcp)
        self.mcp_button.grid(row=1, column=1)
        self.tooltips = []
        for name in ('source', 'output', 'mode', 'deint', 'method', 'replace', 'upscale', 'ocr', 'limit'):
            self.tooltips.append(Tooltip(getattr(self, name), TOOLTIPS[name][0 if self.language == 'de' else 1]))
        self.tooltips.append(Tooltip(self.ocr_hint, TOOLTIPS['ocr'][0 if self.language == 'de' else 1]))
        cpu_de = 'Schonend: niedrige Priorität, höchstens 4 physische Kerne und möglichst 2 Kerne für andere Apps frei. Ausgewogen: ein Kern frei, leicht niedrigere Priorität. Volle Leistung: alle verfügbaren Kerne. GPU-Auslastung wird dadurch nicht begrenzt.'
        cpu_en = 'Gentle: Idle priority, at most 4 physical cores, leaving 2 cores for other apps where possible. Balanced: leaves one core free at Below Normal priority. Full speed: all available cores. This does not cap GPU load.'
        cpu_de += '\nHintergrund / Spielen: bis zu 2 physische Kerne, Idle-Priorität und Pausen zwischen KI-Bildern. Keine Garantie für ruckelfreies Spielen; GPU-Spitzen und Speicherbedarf bleiben möglich.'
        cpu_en += '\nBackground / Gaming: up to 2 physical cores, Idle priority and pauses between AI frames. No guarantee of uninterrupted gaming; GPU spikes and memory usage remain possible.'
        physical = psutil.cpu_count(logical=False) or 1
        hardware = f'\nCPU: {physical} physical / {psutil.cpu_count()} logical'
        self.cpu_texts = (cpu_de + hardware, cpu_en + hardware)
        self.tooltips.append(Tooltip(self.cpu, (cpu_de if self.language == 'de' else cpu_en) + hardware))
        for widget, key in ((self.rate, 'rate'), (self.copy_data_button, 'copydata'), (self.copy_prompt_button, 'copyprompt')):
            self.tooltips.append(Tooltip(widget, TOOLTIPS[key][0 if self.language == 'de' else 1]))
        self.tooltips.append(Tooltip(self.language_button, 'Switch to English' if self.language == 'de' else 'Zu Deutsch wechseln'))
        self.tooltips.append(Tooltip(self.mcp_button, 'Direkte KI-Steuerung über MCP' if self.language == 'de' else 'Direct AI control through MCP'))
        self.after(50, lambda: self.focus_force())

    def write(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', time.strftime('%H:%M:%S') + '  ' + self.t(text) + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def invalidate(self):
        if self.proc:
            return
        self.plan = []
        self.start_button.configure(state='disabled')
        self.sync_controls()
        self.status.configure(text=self.t('Einstellungen geändert · Dateien prüfen.'))

    def sync_controls(self):
        busy=bool(self.proc)
        self.method.configure(state='normal' if not busy and self.deint.get() else 'disabled')
        on=bool(self.ocr.get())
        self.rate.configure(state='normal' if on and not busy else 'disabled',
            button_color=ACCENT if on else '#53616a', progress_color=ACCENT if on else EDGE)
        self.rate_label.configure(text_color=TEXT if on else MUTED)
        self.start_button.configure(fg_color=ACCENT if self.start_button.cget('state')=='normal' else EDGE)
        for tree, label, y in ((self.tree,self.empty_queue,.55),(self.stamps,self.empty_stamps,.4)):
            if tree.get_children():
                label.place_forget()
            elif not label.place_info():
                label.place(relx=.5,rely=y,anchor='center')

    def browse(self, entry):
        folder = filedialog.askdirectory(title=self.t('Ordner mit VHS-Aufnahmen') if entry is self.source else self.t('Ausgabeordner'), parent=self)
        if folder:
            entry.delete(0, 'end')
            entry.insert(0, folder)
            if entry is self.source and (not self.output.get()):
                default = Path(folder).parent / (Path(folder).name + ' – Aufbereitet')
                self.output.insert(0, str(default))
            if self.mode.get() == self.t('Familienarchiv fortführen'):
                self.mode_changed(self.mode.get())
            self.invalidate()

    def mode_changed(self, value):
        self.output.configure(state='normal')
        if value == self.t('Familienarchiv fortführen'):
            self.output.delete(0, 'end')
            self.output.insert(0, self.source.get())
            self.output.configure(state='disabled')
            self.output_button.configure(state='disabled')
            self.mode_hint.configure(text=self.t('Frühere Fassungen werden archiviert.'))
        else:
            self.output_button.configure(state='normal')
            if self.output.get() == self.source.get():
                self.output.delete(0, 'end')
                if self.source.get():
                    p = Path(self.source.get())
                    self.output.insert(0, str(p.parent / (p.name + ' – Aufbereitet')))
            self.mode_hint.configure(text=self.t('Geprüfte MP4s im Ausgabeordner.'))
        self.invalidate()

    def config(self):
        source = Path(self.source.get()).expanduser()
        if not self.source.get() or not source.is_dir():
            raise ValueError(self.t('Bitte einen vorhandenen Aufnahmeordner wählen.'))
        if not self.output.get():
            raise ValueError(self.t('Bitte einen Ausgabeordner wählen.'))
        output = Path(self.output.get()).expanduser()
        archive = self.mode.get() == self.t('Familienarchiv fortführen')
        if not archive and source.resolve() == output.resolve():
            raise ValueError(self.t('Für den Export bitte einen anderen Ausgabeordner wählen.'))
        if archive and not archive_layout.initialized(source):
            prompt=self.t('Archivstruktur anlegen?\n\nNeue Archive verwenden _OriginalCuts, _Deinterlaced, _CutCorrections und _Administration. Vorhandene deutsche Ordner werden weiterverwendet. Jetzt werden nur Ordner angelegt; Videos werden erst nach »Restaurierung starten« bearbeitet und archiviert.')
            if not messagebox.askyesno(self.t('Familienarchiv einrichten'),prompt,parent=self):
                raise ValueError(self.t('Archiveinrichtung abgebrochen.'))
            archive_layout.initialize(source)
        limit = int(self.limit.get())
        if limit < 0:
            raise ValueError(self.t('Dateibegrenzung muss 0 oder größer sein.'))
        options = dict(deinterlace=bool(self.deint.get()), replace=bool(self.replace.get()), upscale=bool(self.upscale.get()), ocr=bool(self.ocr.get()))
        if not any(options.values()):
            raise ValueError(self.t('Bitte mindestens eine Bearbeitung aktivieren.'))
        options.update(notifications=bool(self.notifications.get()),language=self.language)
        return dict(source=str(source.resolve()), output=str(output.resolve()), archive=archive, method=self.method.get(), recursive=bool(self.recursive.get()), limit=limit, gentle=self.cpu.get() == self.t(self.t('Schonend')), cpu_mode=dict(zip([self.t(x) for x in self.cpu_names], ['gentle', 'balanced', 'full', 'background']))[self.cpu.get()], ocr_rate=[0.25, 0.5, 1.0, 2.0, 4.0][round(self.rate.get())], **options)

    def launch(self, cfg, scan):
        self.temp = Path(tempfile.mkdtemp(prefix='VHS-Studio-'))
        self.events = self.temp / 'events.jsonl'
        self.events.touch()
        self.offset = 0
        self.scanning = scan
        self.finished = False
        self.workspaces = []
        self.publishing = False
        cfg['scan_only'] = scan
        config = self.temp / 'config.json'
        config.write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf8')
        self.run_config = cfg
        args = [sys.executable]
        if not getattr(sys, 'frozen', False):
            args.append(str(Path(__file__).resolve()))
        args += ['--worker', str(config), str(self.events)]
        self.stderr = (self.temp / 'error.log').open('w', encoding='utf8')
        self.proc = subprocess.Popen(args, stdout=self.stderr, stderr=self.stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        for option in self.options:
            option.configure(state='disabled')
        self.scan_button.configure(state='disabled')
        self.start_button.configure(state='disabled')
        self.stop_button.configure(state='normal')
        self.sync_controls()
        self.progress.configure(mode='indeterminate' if scan else 'determinate')
        if scan:
            self.progress.start()
        else:
            self.progress.set(0)

    def scan(self):
        try:
            cfg = self.config()
            self.tree.delete(*self.tree.get_children())
            self.queue_title.configure(text=self.t('Arbeitsbereich'))
            self.status.configure(text=self.t('Aufnahmen werden geprüft …'))
            self.write(self.t('Quelle prüfen: ') + cfg['source'])
            self.launch(cfg, True)
        except Exception as exc:
            messagebox.showerror(self.t('Ordner prüfen'), str(exc), parent=self)

    def start(self):
        if not self.plan:
            return
        try:
            cfg = self.config()
            cfg['jobs'] = self.plan
            self.jobs_done = 0
            self.write(self.t(f'Restaurierung gestartet · {len(self.plan)} Dateien'))
            self.launch(cfg, False)
        except Exception as exc:
            messagebox.showerror(self.t('Aufbereitung'), str(exc), parent=self)

    def handle_event(self, event):
        kind = event['event']
        if kind == 'scan':
            self.status.configure(text=self.t(f'{event['count']} Aufnahmen gefunden …'))
        elif kind == 'plan':
            self.plan = event['jobs']
            for i, job in enumerate(self.plan):
                seconds = int(job['seconds'])
                length = self.t(f'{int(seconds) // 60}:{seconds % 60:06.3f}')
                self.tree.insert('', 'end', iid=str(i), values=(job['name'], length, self.t(job['action']), self.t('Bereit')))
            for error in event['errors']:
                self.write(error)
            self.queue_title.configure(text=self.t(f'Warteschlange · {len(self.plan)} Dateien'))
            self.status.configure(text=self.t(f'{len(self.plan)} Aufnahmen bereit.') if self.plan else self.t('Keine passenden Aufnahmen gefunden.'))
            self.finished = True
        elif kind == 'job':
            self.publishing = False
            self.stop_button.configure(state='normal')
            self.tree.set(str(event['index']), 'status', self.t('Läuft'))
            self.tree.see(str(event['index']))
            self.status.configure(text=event['name'])
            self.write(self.t(f'Datei {event['index'] + 1}/{event['total']} · {event['name']}'))
        elif kind == 'workspace':
            self.workspaces.append(Path(event['path']))
        elif kind == 'progress':
            self.progress.set(event['progress'])
            self.detail.configure(text=self.t(f'{event['label']}  ·  {event['progress'] * 100:.0f} %'))
            self.publishing = event['label'] == self.t('Prüfsumme und Ablage')
            self.stop_button.configure(state='disabled' if self.publishing else 'normal')
        elif kind == 'result':
            self.tree.set(str(event['index']), 'status', self.t(event['status']))
            self.write(event['status'] + ' · ' + event['detail'])
            self.jobs_done += 1
            self.publishing = False
        elif kind == 'done':
            self.finished = True
            self.progress.set(1)
            self.status.configure(text=self.t(f'Fertig · {event['total'] - event['failed']} erfolgreich, {event['failed']} Fehler.'))
            self.detail.configure(text=self.t('Ausgabe und Laufprotokoll liegen im Zielordner.'))
            self.write(self.status.cget('text'))
        elif kind == 'cancelled':
            self.finished = True
            self.status.configure(text=self.t('Lauf abgebrochen.'))
            self.detail.configure(text=self.t('Bereits fertiggestellte Ausgaben bleiben im Zielordner.'))
        elif kind == 'fatal':
            self.finished = True
            self.status.configure(text=self.t('Bearbeitung konnte nicht abgeschlossen werden.'))
            self.write(event['message'])
            self.tabs.set(self.t('Protokoll'))

    def poll(self):
        if self.proc:
            try:
                with self.events.open('r', encoding='utf8') as f:
                    f.seek(self.offset)
                    while True:
                        line = f.readline()
                        if not line or not line.endswith('\n'):
                            break
                        self.offset = f.tell()
                        self.handle_event(json.loads(line))
            except (OSError, json.JSONDecodeError):
                pass
            if not self.scanning and self.run_config.get('ocr') and self.tabs.get() == self.t('Datumsfunde') and time.monotonic() - self.last_stamps_refresh > 3:
                self.last_stamps_refresh = time.monotonic()
                self.load_stamps(notify=False)
            if self.proc.poll() is not None:
                self.progress.stop()
                self.progress.configure(mode='determinate')
                if not self.finished:
                    self.status.configure(text=self.t('Bearbeitung beendet · Details im Protokoll.'))
                    try:
                        self.write((self.temp / 'error.log').read_text('utf8', errors='replace')[-2000:])
                    except OSError:
                        pass
                if not self.scanning:
                    self.load_stamps()
                self.stderr.close()
                self.proc = None
                for option in self.options:
                    option.configure(state='normal')
                if self.mode.get() == self.t('Familienarchiv fortführen'):
                    self.output.configure(state='disabled')
                    self.output_button.configure(state='disabled')
                self.scan_button.configure(state='normal')
                self.start_button.configure(state='normal' if self.scanning and self.plan else 'disabled')
                self.stop_button.configure(state='disabled')
                self.publishing = False
                shutil.rmtree(self.temp, ignore_errors=True)
                self.sync_controls()
            for tree,label in ((self.tree,self.empty_queue),(self.stamps,self.empty_stamps)):
                if tree.get_children():
                    label.place_forget()
        self.after(150, self.poll)

    def stop(self):
        if not self.proc or self.publishing:
            return
        if not messagebox.askyesno(self.t('Aufbereitung abbrechen'), self.t('Die laufende Ausgabe verwerfen und den Lauf beenden?'), parent=self):
            return
        (self.temp / 'stop').touch()
        self.stop_button.configure(state='disabled')
        self.status.configure(text=self.t('Lauf wird sicher beendet …'))
        self.write(self.t('Abbruch angefordert. Laufende Dateioperationen werden beendet.'))

    def close(self):
        if self.proc:
            if self.publishing:
                messagebox.showinfo(self.t('Ablage läuft'), self.t('Die geprüfte Ausgabe wird gerade abgelegt. Bitte kurz warten.'), parent=self)
                return
            self.stop()
            if self.proc and self.proc.poll() is None:
                return
        self.save_settings()
        self.destroy()

    def open_output(self):
        folder = Path(self.output.get())
        if self.output.get() and folder.is_dir():
            os.startfile(str(folder))
        else:
            messagebox.showinfo(self.t('Ausgabe'), self.t('Bitte zuerst einen Ausgabeordner wählen.'), parent=self)

    def load_stamps(self, notify=True):
        destination = self.run_config['output'] if self.proc and self.run_config else self.output.get()
        if not destination:
            return
        dbpath = archive_layout.data_folder(Path(destination).resolve())/'VHS-Studio.sqlite3'
        if not dbpath.exists():
            return
        try:
            with closing(sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True, timeout=.2)) as db:
                db.row_factory=sqlite3.Row
                has_reviews=db.execute("SELECT 1 FROM sqlite_master WHERE type='view' AND name='ocr_latest_reviews'").fetchone()
                if has_reviews:
                    query='''SELECT v.id AS video_id,v.path,v.size,v.mtime_ns,s.second,s.date,s.raw,
                        r.id AS review_id,r.decision,r.confirmed_date,r.boundary_second,
                        r.uncertainty_second,r.provider,r.model,r.evidence,r.created
                        FROM ocr_stamps s JOIN ocr_videos v ON v.id=s.video
                        LEFT JOIN ocr_latest_reviews r ON r.video=s.video
                        AND r.second=s.second AND r.camera_date=s.date
                        ORDER BY v.path,s.second LIMIT 5000'''
                else:
                    query='''SELECT v.id AS video_id,v.path,v.size,v.mtime_ns,s.second,s.date,s.raw,
                        NULL AS review_id,NULL AS decision,NULL AS confirmed_date,
                        NULL AS boundary_second,NULL AS uncertainty_second,NULL AS provider,
                        NULL AS model,NULL AS evidence,NULL AS created
                        FROM ocr_stamps s JOIN ocr_videos v ON v.id=s.video
                        ORDER BY v.path,s.second LIMIT 5000'''
                rows = db.execute(query).fetchall()
            active=set()
            identities={}
            statuses={'verified':'Bestätigt','corrected':'Korrigiert','uncertain':'Unklar','rejected':'Fehlfund'}
            for row in rows:
                r=dict(row); seconds=r['second']
                if r['path'] not in identities:
                    try:
                        stat=Path(r['path']).stat()
                        identities[r['path']]=(stat.st_size,stat.st_mtime_ns)==(r['size'],r['mtime_ns'])
                    except OSError:
                        identities[r['path']]=False
                r['source_current']=identities[r['path']]
                key=json.dumps([r['video_id'],seconds,r['date']])
                active.add(key)
                self.stamp_rows[key]=dict(r,database=str(dbpath))
                boundary='—' if r['boundary_second'] is None else f"{r['boundary_second']:.3f}"
                reviewer=' / '.join(x for x in (r['provider'],r['model']) if x) or '—'
                state=statuses.get(r['decision'],'Ungeprüft') if r['source_current'] else 'Quelle verändert / fehlt'
                values=(Path(r['path']).name,f'{int(seconds)//60}:{seconds%60:06.3f}',r['date'],r['confirmed_date'] or '—',boundary,self.t(state),reviewer)
                tag=r['decision'] or 'unreviewed' if r['source_current'] else 'uncertain'
                if self.stamps.exists(key):
                    if tuple(self.stamps.item(key,'values'))!=values:
                        self.stamps.item(key,values=values,tags=(tag,))
                else:
                    self.stamps.insert('', 'end', iid=key,values=values,tags=(tag,))
            for key in self.stamps.get_children():
                if key not in active:
                    self.stamps.delete(key); self.stamp_rows.pop(key,None)
            self.sync_controls()
            if rows and notify:
                self.write(self.t(f'{len(rows)} Datumsfunde im Reiter Datumsfunde (maximal 5000 angezeigt).'))
        except sqlite3.Error as exc:
            if notify:
                self.write(str(exc))

    def show_finding(self):
        selected=self.stamps.selection()
        if not selected:
            return
        record=self.stamp_rows[selected[0]]
        dialog=ctk.CTkToplevel(self)
        dialog.title(self.t('Prüfdetails'))
        dialog.geometry('780x540'); dialog.transient(self)
        box=ctk.CTkTextbox(dialog,wrap='word',font=('Inter',13))
        box.pack(fill='both',expand=True,padx=20,pady=20)
        fields=[('Aufnahme',record['path']),('Position',f"{record['second']:.3f} s"),
            ('OCR-Datum',record['date']),('Gelesener Stempel',record['raw']),
            ('Geprüftes Datum',record['confirmed_date'] or '—'),
            ('Prüfer / Modell',' / '.join(x for x in (record['provider'],record['model']) if x) or '—'),
            ('Grenze (s)',record['boundary_second'] if record['boundary_second'] is not None else '—'),
            ('Unsicherheit (s)',record['uncertainty_second'] if record['uncertainty_second'] is not None else '—'),
            ('Begründung',record['evidence'] or '—'),('Geprüft am',record['created'] or '—')]
        text='\n\n'.join(f'{self.t(label)}\n{value}' for label,value in fields)
        with closing(sqlite3.connect(record['database'])) as db:
            db.row_factory=sqlite3.Row
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='ocr_reviews'").fetchone():
                history=[dict(r) for r in db.execute('SELECT * FROM ocr_reviews WHERE video=? AND second=? AND camera_date=? ORDER BY id',(record['video_id'],record['second'],record['date']))]
                text+='\n\n'+self.t('Prüfverlauf')+'\n'
                for item in history:
                    text+=f"\n#{item['id']} · {item['created']} · {item['provider']} / {item['model'] or '—'}\n{item['decision']} · {item['confirmed_date'] or '—'}\n{item['evidence']}\n"
        box.insert('1.0',text);box.configure(state='disabled')

    def rate_changed(self, value):
        rate = [0.25, 0.5, 1.0, 2.0, 4.0][round(float(value))]
        formatted = self.t(f'{rate:g}').replace('.', ',') if self.language == 'de' else self.t(f'{rate:g}')
        self.rate_label.configure(text=self.t(f'Scan-Raster · {formatted} Bild/s') if self.language == 'de' else self.t(f'Scan frequency · {formatted} fps'))
        self.invalidate()

    def switch_language(self):
        if self.proc:
            return
        from i18n import EN
        inverse = {value:key for key,value in EN.items()}
        for de, en in TOOLTIPS.values():
            inverse[en] = de
        def canonical(text):
            return inverse.get(str(text), str(text))
        def trans(text):
            text = canonical(text)
            for de, en in TOOLTIPS.values():
                if text == de:
                    return de if self.language == 'de' else en
            return self.t(text)
        old_tabs = list(self.tabs._name_list)
        current_tab = self.tabs.get()
        selections = [(widget, canonical(widget.get())) for widget in (self.mode, self.cpu)]
        self.language = 'en' if self.language == 'de' else 'de'
        # Update existing widgets in one event-loop turn. Preserve layout,
        # focus, entries, selected rows, logs and the prepared queue.
        def visit(widget):
            if widget is self.language_button:
                return
            for option in ('text', 'placeholder_text'):
                try:
                    value = widget.cget(option)
                    if value:
                        widget.configure(**{option:trans(value)})
                except (ValueError, TypeError, tk.TclError, AttributeError):
                    pass
            if isinstance(widget, ctk.CTkOptionMenu):
                widget.configure(values=[trans(x) for x in widget.cget('values')])
            if isinstance(widget, ttk.Treeview):
                for column in widget['columns']:
                    widget.heading(column, text=trans(widget.heading(column, 'text')))
                for row in widget.get_children():
                    # Only textual processing/status columns; paths stay literal.
                    for column in ('action', 'status', 'review'):
                        if column in widget['columns']:
                            widget.set(row, column, trans(widget.set(row, column)))
            for child in widget.winfo_children():
                visit(child)
        for child in self.winfo_children():
            visit(child)
        for old in old_tabs:
            new = trans(old)
            if old != new:
                self.tabs.rename(old, new)
        self.tabs.set(trans(current_tab))
        self.tabs._segmented_button.grid_configure(sticky='ew')
        for widget, value in selections:
            widget.set(trans(value))
        image = Image.new('RGB', (28,18))
        for y in range(18):
            for x in range(28):
                color = ('#171717','#dc3030','#f1c44b')[min(2,y//6)] if self.language == 'de' else '#254780'
                if self.language == 'en':
                    if abs(y-x*18/28)<2 or abs(y-(18-x*18/28))<2 or 11<=x<=16 or 6<=y<=11:
                        color='#f5f5f5'
                    if 12<=x<=15 or 7<=y<=10:
                        color='#d72f43'
                image.putpixel((x,y),tuple(bytes.fromhex(color[1:])))
        self.flag = ctk.CTkImage(light_image=image,dark_image=image,size=(28,18))
        self.language_button.configure(text='DE' if self.language=='de' else 'EN', image=self.flag)
        self.mcp_button.configure(text='KI / MCP' if self.language=='de' else 'AI / MCP')
        self.title(self.t('VHS Studio · Familienaufnahmen aufbereiten'))
        for tooltip in self.tooltips:
            tooltip.leave()
            tooltip.text=trans(tooltip.text)
            if tooltip.widget is self.cpu:
                tooltip.text=self.cpu_texts[0 if self.language=='de' else 1]
            elif tooltip.widget is self.language_button:
                tooltip.text='Switch to English' if self.language=='de' else 'Zu Deutsch wechseln'
            elif tooltip.widget is self.mcp_button:
                tooltip.text='Direkte KI-Steuerung über MCP' if self.language=='de' else 'Direct AI control through MCP'
        self.save_settings()

    def settings_snapshot(self):
        return dict(language=self.language, source=self.source.get(), output=self.output.get(),
            archive=self.mode.get()==self.t('Familienarchiv fortführen'), method=self.method.get(),
            **{k:bool(getattr(self,k).get()) for k in ('deint','replace','upscale','ocr','recursive','notifications')},
            limit=self.limit.get(), rate=round(self.rate.get()),
            cpu=[self.t(x) for x in self.cpu_names].index(self.cpu.get()))

    def restore_settings(self, saved):
        if not saved:
            return
        for key in ('source', 'output', 'limit'):
            if key in saved:
                widget=getattr(self,key)
                widget.delete(0,'end')
                if str(saved[key]):
                    widget.insert(0,str(saved[key]))
        self.mode.set(self.t('Familienarchiv fortführen') if saved.get('archive') else self.t('In Ausgabeordner exportieren'))
        if saved.get('method') in ('QTGMC','BWDIF'):
            self.method.set(saved['method'])
        for name in ('deint','replace','upscale','ocr','recursive','notifications'):
            if name in saved:
                getattr(self,name).select() if saved[name] else getattr(self,name).deselect()
        self.cpu.set(self.t(self.cpu_names[max(0,min(3,int(saved.get('cpu',0))))]))
        self.rate.set(max(0,min(4,int(saved.get('rate',2)))))
        self.mode_changed(self.mode.get())
        self.rate_changed(self.rate.get())
        self.status.configure(text=self.t('Letzte Einstellungen geladen · Dateien prüfen.'))

    def save_settings(self):
        try:
            current=self.settings_snapshot()
            if current != self.saved_settings:
                preferences.save(current)
                self.saved_settings=current
        except (OSError, ValueError):
            pass

    def autosave(self):
        self.save_settings()
        if self.tabs.get()==self.t('Datumsfunde'):
            self.load_stamps(notify=False)
        self.sync_controls()
        self.after(2000,self.autosave)

    def start_update_check(self):
        if not (getattr(sys,'frozen',False) or os.environ.get('VHS_STUDIO_BOOTSTRAP')=='1') or '--skip-update' in sys.argv:
            return
        import threading
        def check():
            try:
                import app_updates
                info=app_updates.latest()
                if info:
                    self.update_info=info
                    self.update_result=('downloading',None)
                    staged=app_updates.stage(info)
                    self.update_result=('ready',staged)
                else:
                    self.update_result=('current',None)
            except Exception as error:
                self.update_result=('error',str(error))
        threading.Thread(target=check,daemon=True).start()
        self.after(500,self.poll_update)

    def poll_update(self):
        result=self.update_result
        if result is None:
            self.after(500,self.poll_update);return
        state,payload=result
        if state=='downloading':
            self.version_label.configure(text=f'v{VERSION} · '+self.t('Update wird geladen …'))
            self.after(500,self.poll_update);return
        if state=='ready':
            import app_updates
            if self.proc or app_updates.other_instances():
                self.version_label.configure(text=self.t('Update bereit · wartet auf laufende Aufgaben'))
                self.after(2000,self.poll_update);return
            try:
                self.save_settings()
                app_updates.launch_helper(payload,self.update_info)
                self.destroy()
            except Exception as error:
                self.write(self.t('Update konnte nicht installiert werden: ')+str(error))
            return
        if state=='error':
            self.write(self.t('Updateprüfung nicht verfügbar: ')+payload)

    def show_autostart(self):
        dialog=ctk.CTkToplevel(self)
        dialog.title(self.t('Autostart'))
        dialog.geometry('700x540')
        dialog.transient(self)
        try:
            active=preferences.startup_active()
        except Exception:
            active=False
        title='Autostart ist aktiv' if active else 'Autostart ist ausgeschaltet'
        self.label(dialog,self.t(title),19,weight='bold').pack(anchor='w',padx=24,pady=(22,12))
        info=('Startet nach deiner Windows-Anmeldung ohne Fenster. Verwendet eine gespeicherte Kopie dieser Konfiguration und verarbeitet die gewählte Anzahl Dateien pro Anmeldung. Erfolgreiche Autostart-Jobs werden beim nächsten Mal übersprungen; Fehler bleiben für einen erneuten Versuch erhalten.\n\nKein Administrator nötig. Kein Dienst. Die EXE muss am selben Ort bleiben. Netzwerkordner müssen bei der Anmeldung erreichbar sein. Änderungen hier im Fenster ändern einen aktiven Autostart erst nach »Profil übernehmen«.\n\nOCR und Laufprotokolle: Zielordner / _Verwaltung / VHS-Studio. Einstellungen, Autostartprofil und Hintergrundstatus: ' if self.language=='de' else 'Runs after your Windows sign-in without a window. Uses a saved snapshot of this configuration and processes the selected number of files per sign-in. Successful startup jobs are skipped next time; failed jobs remain eligible.\n\nNo administrator access or service. Keep the executable at its location. Network folders must be available at sign-in. Editing the GUI does not update an active startup profile until you apply it.\n\nOCR and run logs: destination / _Verwaltung / VHS-Studio. Settings, startup profile and background status: ')
        self.label(dialog,info+str(preferences.state_dir()),13,wraplength=645,justify='left').pack(anchor='w',padx=24,pady=8)
        status=preferences.read_json(preferences.state_dir()/'autostart-status.json')
        if status:
            self.label(dialog,json.dumps(status,ensure_ascii=False)[:240],11,MUTED,wraplength=640,justify='left').pack(padx=24,pady=8)
        def apply(enabled):
            try:
                preferences.configure_startup(self.config() if enabled else None,enabled=enabled)
                self.save_settings()
                dialog.destroy()
                self.write(self.t('Autostartprofil gespeichert.') if enabled else self.t('Autostart ausgeschaltet.'))
            except Exception as error:
                messagebox.showerror(self.t('Autostart'),str(error),parent=dialog)
        row=ctk.CTkFrame(dialog,fg_color='transparent')
        row.pack(side='bottom',fill='x',padx=24,pady=24)
        ctk.CTkButton(row,text=self.t('Deaktivieren'),fg_color=EDGE,command=lambda:apply(False)).pack(side='left')
        ctk.CTkButton(row,text=self.t('Profil übernehmen') if active else self.t('Autostart aktivieren'),command=lambda:apply(True)).pack(side='right')

    def show_review(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title(self.t('KI-Prüfauftrag ansehen'))
        dialog.geometry('800x580')
        dialog.transient(self)
        folder = archive_layout.data_folder(self.output.get())
        try:
            if not self.output.get():
                raise ValueError('No destination')
            text = review_prompt(folder, self.language)
        except (OSError, ValueError):
            text = ('VORSCHAU – nach dem OCR-Lauf stehen hier die konkreten Pfade und Funde.\n\nPrüfe die OCR-Daten und die zugehörigen Originalvideos lokal. Lies Kamerastempel visuell nach; sie können falsch eingestellt sein. Untersuche Frames vor und nach jedem vermuteten Datums- oder Szenenwechsel. Grenze den Übergang bildgenau ein und dokumentiere die Unsicherheit. Noch keine Dateien schneiden oder verändern.\n\nNach einem OCR-Lauf: Reiter Datumsfunde → KI-Prüfauftrag kopieren.' if self.language == 'de' else 'PREVIEW – actual paths and findings appear after OCR completes.\n\nReview local OCR findings and their original videos. Visually verify camera dates; they may be set incorrectly. Inspect frames before and after each suspected date or scene change. Refine boundaries to frame precision and document uncertainty. Do not cut or modify files during review.\n\nAfter an OCR run: Date findings → Copy AI review prompt.')
        box = ctk.CTkTextbox(dialog, wrap='word', font=('Inter', 13))
        box.pack(fill='both', expand=True, padx=20, pady=20)
        box.insert('1.0', text)
        box.configure(state='disabled')
        def copy():
            self.clipboard_clear()
            self.clipboard_append(text)
        ctk.CTkButton(dialog, text=self.t('KI-Prüfauftrag kopieren'), command=copy).pack(pady=(0, 20))

    def copy_ocr(self, prompt):
        folder = archive_layout.data_folder(self.output.get())
        try:
            if prompt:
                text = review_prompt(folder, self.language)
            else:
                text = (folder / 'OCR-Fundstellen.json').read_text('utf8')
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
            self.copy_notice.configure(text=self.t(self.t('KI-Prüfauftrag kopiert.') if prompt else self.t('Funddaten kopiert.')))
        except (OSError, ValueError):
            messagebox.showinfo(self.t(self.t('Datumsfunde')), self.t(self.t('Noch keine OCR-Daten vorhanden. Erst einen Lauf mit Datums-OCR abschließen.')), parent=self)

    def show_mcp(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title('VHS Studio · MCP')
        dialog.geometry('780x540')
        dialog.transient(self)
        exe = Path(os.environ.get('VHS_STUDIO_EXE',sys.executable)).resolve() if os.environ.get('VHS_STUDIO_BOOTSTRAP')=='1' else Path(sys.executable).resolve()
        command = [str(exe)]
        if not getattr(sys, 'frozen', False) and os.environ.get('VHS_STUDIO_BOOTSTRAP')!='1':
            command.append(str(Path(__file__).resolve()))
        config = {'mcpServers': {'vhs-studio': {'command': str(exe), 'args': command[1:] + ['--mcp']}}}
        info = 'Diese EXE mit --mcp als lokalen stdio-MCP-Server eintragen. Optionen abfragen, Quellen prüfen, Läufe starten und Status/Logs live lesen.' if self.language == 'de' else 'Register this EXE with --mcp as a local stdio MCP server. Inspect options, scan folders, start runs and read live status/logs.'
        info += ('\n\nOhne MCP-Eintrag: Eine lokale KI kann --describe und --api aufrufen. Eine laufende GUI wird lokal unter %LOCALAPPDATA%/VHS Studio/instances vermerkt. Keine automatische Anmeldung bei KI-Apps. GUI-Läufe sind separat von API-/MCP-Läufen.' if self.language == 'de' else '\n\nWithout MCP registration: a local AI can use --describe and --api. Running GUI instances leave a local descriptor in %LOCALAPPDATA%/VHS Studio/instances. No automatic AI-client registration. GUI jobs are separate from API/MCP jobs.')
        self.label(dialog, info, 13, wraplength=650, justify='left').pack(padx=22, pady=18, anchor='w')
        box = ctk.CTkTextbox(dialog, font=('Consolas', 12))
        box.pack(fill='both', expand=True, padx=22)
        text = json.dumps(config, ensure_ascii=False, indent=2)
        box.insert('1.0', text)

        def copy():
            self.clipboard_clear()
            self.clipboard_append(text)
        ctk.CTkButton(dialog, text='Konfiguration kopieren' if self.language == 'de' else 'Copy configuration', command=copy).pack(padx=22, pady=17, anchor='e')

    def help(self):
        text = HELP_EN if self.language == 'en' else HELP_DE
        text = OCR_PURPOSE[0 if self.language == 'de' else 1] + '\n\n' + text
        text += f'\n\nVHS Studio v{VERSION} · MIT\n' + ('Fremdkomponenten und Modell behalten ihre eigenen Lizenzen.' if self.language=='de' else 'Third-party tools and model weights retain their own licenses.')
        dialog = ctk.CTkToplevel(self)
        dialog.title(self.t('So funktioniert’s'))
        dialog.geometry('780x640')
        dialog.minsize(620, 420)
        dialog.transient(self)
        dialog.configure(fg_color=BG)
        self.label(dialog, self.t('So funktioniert’s'), 20, weight='bold').pack(anchor='w', padx=24, pady=(22, 12))
        box = ctk.CTkTextbox(dialog, wrap='word', font=('Inter', 13), fg_color=PANEL, text_color=TEXT)
        box.pack(fill='both', expand=True, padx=24, pady=(0, 24))
        box.insert('1.0', text)
        box.configure(state='disabled')

    def test_ready(self):
        self.write(self.t('Oberfläche startbereit.'))
if __name__ == '__main__':
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('VHSStudio.Portable')
    except Exception:
        pass
    Studio().mainloop()
