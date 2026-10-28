import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
import GeneSpace
import CodonExpressionIndex
from GeneOptimization import Optimizer, translate
import pickle
import os
import sys
from math import log, exp
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
import multiprocessing
import traceback
from queue import Empty


def resource_path(relative_path):
    return os.path.join(os.path.dirname(__file__), relative_path)


def set_window_icon(parent):
    """Sets the windows icon at runtime"""
    try:
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            icon_path = resource_path('appearance/genex.ico')
        if os.path.exists(icon_path):
            parent.iconbitmap(icon_path)
    except:
        pass


class ClipboardShortcuts:
    def __init__(self, parent):
        self.parent = parent
        self.is_mac = sys.platform == 'darwin'
        self.modifier_mask = 0x8 if self.is_mac else 0x4

        self.parent.bind_all('<KeyPress>', self._handle_keypress, add='+')

    def _get_text_widget(self, widget):
        while widget is not None:
            if isinstance(widget, ctk.CTkEntry):
                return widget._entry

            if isinstance(widget, ctk.CTkTextbox):
                return widget._textbox

            if isinstance(widget, (tk.Entry, tk.Text)):
                return widget

            widget = getattr(widget, 'master', None)

        return None

    def _handle_keypress(self, event):
        if not (event.state & self.modifier_mask):
            return

        widget = self._get_text_widget(self.parent.focus_get())

        if widget is None:
            return

        key = event.char.lower()

        if key == 'a':
            self._select_all(widget)
            return 'break'

        if key == 'c':
            self._copy(widget)
            return 'break'

        if key == 'x':
            self._cut(widget)
            return 'break'

        if key == 'v':
            self._paste(widget)
            return 'break'

    def _select_all(self, widget):
        try:
            widget.selection_range(0, 'end')
            widget.icursor('end')
        except tk.TclError:
            try:
                widget.tag_add('sel', '1.0', 'end-1c')
                widget.mark_set('insert', 'end-1c')
            except tk.TclError:
                pass

    def _copy(self, widget):
        try:
            widget.event_generate('<<Copy>>')
        except tk.TclError:
            pass

    def _cut(self, widget):
        try:
            widget.event_generate('<<Cut>>')
        except tk.TclError:
            pass

    def _paste(self, widget):
        try:
            widget.event_generate('<<Paste>>')
        except tk.TclError:
            pass


class PopupWindow(ctk.CTkToplevel):
    def __init__(self, master, width=300, height=120, corner_radius=10, border_width=3):
        super().__init__(master)

        self.master_window = master
        self.popup_width = width
        self.popup_height = height
        self.overrideredirect(True)

        # Platform-specific transparent background
        if sys.platform.startswith("win"):
            self.transparent_color = self._apply_appearance_mode(self._fg_color)
            self.attributes("-transparentcolor", self.transparent_color)

        elif sys.platform.startswith("darwin"):
            self.transparent_color = "systemTransparent"
            self.attributes("-transparent", True)

        else:
            self.transparent_color = "#000001"
            self.attributes("-type", "splash")

        # Rounded frame
        self.frame = ctk.CTkFrame(self, corner_radius=corner_radius, border_width=border_width, bg_color=self.transparent_color)
        self.frame.pack(expand=True, fill="both")

        # Text
        self.label = ctk.CTkLabel(self.frame, text="", justify="center", wraplength=width - 40, font=ctk.CTkFont(family='Arial', size=15, weight='normal'), text_color='red')
        self.label.pack(expand=True, fill="both", padx=20, pady=15)

        self.resizable(False, False)
        self.transient(master)

        # Hide when clicking anywhere
        self.master.bind_all("<Button-1>", self._on_click, add="+")

        # Hide when main window is moved/resized
        self.master.bind("<Configure>", self._on_master_configure, add="+")

        # Hide when focus moves to another window
        self.master.bind('<Deactivate>', self._on_master_configure, add="+")

        self.withdraw()

    def _on_click(self, event=None):
        if self.winfo_exists():
            self.withdraw()

    def _on_master_configure(self, event=None):
        if self.winfo_exists() and self.state() != "withdrawn":
            self.withdraw()

    def show(self, text):
        self.label.configure(text=text)

        # Make sure geometry is up to date
        self.master_window.update_idletasks()
        self.update_idletasks()

        # Main window position and size
        master_x = self.master_window.winfo_rootx()
        master_y = self.master_window.winfo_rooty()
        master_width = self.master_window.winfo_width()
        master_height = self.master_window.winfo_height()

        # Center popup over main window
        x = master_x + (master_width - self.popup_width) // 2
        y = master_y + (master_height - self.popup_height) // 2

        self.geometry(f"{self.popup_width}x{self.popup_height}+{x}+{y}")

        self.deiconify()
        self.lift()
        self.focus_force()


class ToolTip:
    def __init__(self, widget, text="widget info", waittime=1000, wraplength=300, corner_radius=7, border_width=1):
        self.widget = widget
        self.text = text
        self.waittime = waittime
        self.wraplength = wraplength

        self.id = None
        self.tw = None

        self.corner_radius = corner_radius
        self.border_width = border_width

        # Bind mouse events
        self.widget.bind("<Enter>", self.enter, add="+")
        self.widget.bind("<Leave>", self.leave, add="+")
        self.widget.bind("<ButtonPress>", self.leave, add="+")

        # Hide when focus moves to another window
        self.widget.bind('<Deactivate>', self.leave, add="+")

        # Hide when left mouse button is pressed
        self.widget.bind('<Button-1>', self.leave, add="+")


    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        if self.id is not None:
            try:
                self.widget.after_cancel(self.id)
            except Exception:
                pass

            self.id = None

    def showtip(self):
        self.id = None

        if self.tw is None or not self.tw.winfo_exists():
            self._create_window()

        self.label.configure(text=self.text)
        self.tw.update_idletasks()

        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tw.geometry(f"+{x}+{y}")

        self.tw.deiconify()
        self.tw.lift()

    def _create_window(self):

        self.tw = ctk.CTkToplevel(self.widget)

        # Remove title bar
        self.tw.overrideredirect(True)

        self.tw.resizable(False, False)
        self.tw.transient(self.widget)

        # Platform-specific transparent background
        if sys.platform.startswith("win"):
            self.transparent_color = self.tw._apply_appearance_mode(self.tw._fg_color)
            self.tw.attributes("-transparentcolor", self.transparent_color)

        elif sys.platform.startswith("darwin"):
            self.transparent_color = "systemTransparent"
            self.tw.attributes("-transparent", True)

        else:
            self.transparent_color = "#000001"
            self.tw.attributes("-type", "tooltip")

        # Rounded frame
        self.frame = ctk.CTkFrame(self.tw, corner_radius=self.corner_radius, border_width=self.border_width, bg_color=self.transparent_color)
        self.frame.pack(expand=True, fill="both")

        # Tooltip text
        self.label = ctk.CTkLabel(self.frame, text=self.text, justify="left", wraplength=self.wraplength)
        self.label.pack(padx=7, pady=7)

        # Hide immediately when tooltip itself receives a click
        self.tw.bind("<ButtonPress>", self.leave)
        self.frame.bind("<ButtonPress>", self.leave)
        self.label.bind("<ButtonPress>", self.leave)
        self.widget.bind("<Button>", self.leave)

        self.tw.withdraw()

    def hidetip(self):
        if self.tw is not None and self.tw.winfo_exists():
            self.tw.withdraw()

    def destroy(self):
        """Remove the tooltip completely."""
        self.unschedule()
        if self.tw is not None and self.tw.winfo_exists():
            self.tw.destroy()
        self.tw = None


class PlaceholderTextbox(ctk.CTkFrame):
    def __init__(self, master, placeholder_text='', placeholder_color=None, **kwargs):
        super().__init__(master)
        self.textbox = ctk.CTkTextbox(self, **kwargs)

        self.placeholder_text = placeholder_text
        self.placeholder_color = placeholder_color if placeholder_color is not None else '#808080'
        self.placeholder_tag = '_placeholder'

        self.textbox.pack(expand=True, fill='both')

        self.textbox.tag_config(self.placeholder_tag, foreground=self.placeholder_color)

        self.textbox.bind('<FocusIn>', self._focus_in, add='+')
        self.textbox.bind('<KeyPress>', self._key_press, add='+')
        self.textbox.bind('<FocusOut>', self._focus_out, add='+')

        self._show_placeholder()

    def _show_placeholder(self):
        if self.placeholder_text and not self.textbox.get('1.0', 'end-1c'):
            self.textbox.insert('1.0', self.placeholder_text, self.placeholder_tag)

    def _hide_placeholder(self):
        if self._is_placeholder():
            self.textbox.delete('1.0', 'end')

    def _is_placeholder(self):
        return self.textbox.get('1.0', 'end-1c') == self.placeholder_text and self.textbox.tag_ranges(self.placeholder_tag)

    def _focus_in(self, event=None):
        self._hide_placeholder()

    def _key_press(self, event=None):
        if self._is_placeholder():
            self._hide_placeholder()

    def _focus_out(self, event=None):
        self._show_placeholder()

    def get(self, *args):
        if self._is_placeholder():
            return ''

        return self.textbox.get(*args)

    def delete(self, *args):
        if self._is_placeholder():
            return

        self.textbox.delete(*args)

        if not self.textbox.get('1.0', 'end-1c'):
            self._show_placeholder()

    def insert(self, index, chars, *args):
        if self._is_placeholder():
            self._hide_placeholder()

        self.textbox.insert(index, chars, *args)

    def __getattr__(self, name):
        return getattr(self.textbox, name)


class TestPopupWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)

        self.master_window = master

        self.overrideredirect(True)
        self.resizable(False, False)
        self.transient(master)

        self.frame = ctk.CTkFrame(self, corner_radius=12)
        self.frame.pack(padx=2, pady=2)

        self.label = ctk.CTkLabel(self.frame, text='')
        self.label.pack(padx=30, pady=(20, 10))

        self.button = ctk.CTkButton(self.frame, text='Stop', command=self.hide)
        self.button.pack(padx=30, pady=(0, 20))

        self.protocol('WM_DELETE_WINDOW', self.hide)

        self.master_window.bind('<Deactivate>', self._app_deactivate, add='+')
        self.master_window.bind('<Activate>', self._app_activate, add='+')

        self.withdraw()

    def show(self, text):
        self.label.configure(text=text)

        self.update_idletasks()

        x = self.master_window.winfo_rootx() + (self.master_window.winfo_width() - self.winfo_width()) // 2
        y = self.master_window.winfo_rooty() + (self.master_window.winfo_height() - self.winfo_height()) // 2

        self.geometry(f'+{x}+{y}')

        self.deiconify()
        self.lift()

    def hide(self):
        self.withdraw()

    def _app_deactivate(self, event=None):
        if self.winfo_exists():
            self.withdraw()

    def _app_activate(self, event=None):
        if self.winfo_exists():
            self.deiconify()
            self.lift()


def _process_worker(function, args, kwargs, result_queue):
    try:
        result = function(*args, **kwargs)
        result_queue.put(('result', result))
    except Exception:
        result_queue.put(('error', traceback.format_exc()))


class ProcessPopup(ctk.CTkToplevel):
    def __init__(self, master, stop_callback, text='Please wait...'):
        super().__init__(master)

        self.title('')
        self.master_window = master
        self.stop_callback = stop_callback

        self.resizable(False, False)
        self.transient(master)

        self.label = ctk.CTkLabel(self, text=text)
        self.label.pack(padx=30, pady=(20, 10))

        self.stop_button = ctk.CTkButton(self, text='Stop', command=self.stop_callback)
        self.stop_button.pack(padx=30, pady=(0, 20))

        self.protocol('WM_DELETE_WINDOW', self.stop_callback)

        self.update_idletasks()

        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()

        x = master.winfo_rootx() + (master.winfo_width() - width) // 2
        y = master.winfo_rooty() + (master.winfo_height() - height) // 2

        self.geometry(f'{width}x{height}+{x}+{y}')

        self.update_idletasks()
        self.update()

        self._remove_titlebar()

        self.update_idletasks()

    def _remove_titlebar(self):
        if sys.platform.startswith('win'):
            self._remove_windows_titlebar()

        elif sys.platform.startswith('darwin'):
            self._remove_macos_titlebar()

        elif sys.platform.startswith('linux'):
            self._remove_linux_titlebar()

    def _remove_windows_titlebar(self):
        import ctypes

        hwnd = self.winfo_id()

        GWL_STYLE = -16
        WS_CAPTION = 0x00C00000

        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
        style &= ~WS_CAPTION

        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_FRAMECHANGED = 0x0020

        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)

    def _remove_macos_titlebar(self):
        try:
            self.tk.call('::tk::unsupported::MacWindowStyle', 'style', self._w, 'plain', 'none')
        except Exception:
            pass

    def _remove_linux_titlebar(self):
        try:
            if self.tk.call('tk', 'windowingsystem') != 'x11':
                return

            self._remove_linux_x11_decorations()

        except Exception:
            pass

    def _remove_linux_x11_decorations(self):
        try:
            import ctypes
            import ctypes.util

            x11_path = ctypes.util.find_library('X11')

            if x11_path is None:
                return

            x11 = ctypes.cdll.LoadLibrary(x11_path)

            x11.XOpenDisplay.restype = ctypes.c_void_p
            x11.XInternAtom.restype = ctypes.c_ulong

            display = x11.XOpenDisplay(None)

            if not display:
                return

            window = self.winfo_id()

            motif_hints = x11.XInternAtom(display, b'_MOTIF_WM_HINTS', False)

            if not motif_hints:
                x11.XCloseDisplay(display)
                return

            class MotifWmHints(ctypes.Structure):
                _fields_ = [
                    ('flags', ctypes.c_ulong),
                    ('functions', ctypes.c_ulong),
                    ('decorations', ctypes.c_ulong),
                    ('input_mode', ctypes.c_long),
                    ('status', ctypes.c_ulong)
                ]

            hints = MotifWmHints()
            hints.flags = 2
            hints.decorations = 0

            x11.XChangeProperty(display, window, motif_hints, motif_hints, 32, 0, ctypes.byref(hints), 5)
            x11.XFlush(display)
            x11.XCloseDisplay(display)

        except Exception:
            pass

    def show(self):
        if not self.winfo_exists():
            return

        self.deiconify()
        self.update_idletasks()
        self.lift()

        try:
            self.grab_set()
        except Exception:
            pass

        self.after(20, self._activate)

    def _activate(self):
        if not self.winfo_exists():
            return

        self.lift()

        try:
            self.focus_force()
        except Exception:
            pass

        try:
            self.stop_button.focus_force()
        except Exception:
            pass

    def close(self):
        if not self.winfo_exists():
            return

        try:
            self.grab_release()
        except Exception:
            pass

        self.withdraw()
        self.destroy()


def run_in_process(master, function, *args, popup_text='Please wait...', **kwargs):
    result_queue = multiprocessing.Queue()

    process = multiprocessing.Process(target=_process_worker, args=(function, args, kwargs, result_queue))
    process.start()

    state = {'finished': False, 'stopped': False, 'result': None, 'error': None}

    previous_focus = master.focus_get()

    def restore_focus():
        try:
            master.focus_force()
        except Exception:
            pass

        if previous_focus is not None:
            try:
                if previous_focus.winfo_exists():
                    previous_focus.focus_force()
                    return
            except Exception:
                pass

        try:
            master.focus_force()
        except Exception:
            pass

    def close_popup():
        if popup.winfo_exists():
            popup.close()

        try:
            master.focus_force()
        except Exception:
            pass

        master.update_idletasks()

    def finish_stopped():
        if process.is_alive():
            master.after(10, finish_stopped)
            return

        process.join()

        state['finished'] = True

        close_popup()

        master.after(20, restore_focus)

    def stop_process():
        if state['finished'] or state['stopped']:
            return

        state['stopped'] = True

        if process.is_alive():
            process.terminate()

        master.after(10, finish_stopped)

    popup = ProcessPopup(master, stop_process, popup_text)

    popup.show()

    while not state['finished']:
        try:
            message_type, value = result_queue.get_nowait()

            if message_type == 'result':
                state['result'] = value
            else:
                state['error'] = value

            state['finished'] = True

        except Empty:
            if not process.is_alive() and not state['stopped']:
                state['finished'] = True

        if not state['finished']:
            master.update()

    if not state['stopped']:
        process.join()

        close_popup()

        master.after(20, restore_focus)

    result_queue.close()

    return state


ctk.set_appearance_mode("System")
ctk.set_default_color_theme(resource_path('appearance/green.json'))
ctk.set_widget_scaling(1)
matplotlib.use('Agg')


class App:
    def __init__(self, parent):
        self.parent = parent
        if sys.platform.startswith("win"):
            parent.geometry("1300x1300")
        else:
            parent.geometry("800x800")
        parent.title('GenOA')
        parent.columnconfigure(index=0, weight=1)
        parent.resizable(width=True, height=True)
        # Remove focus from widgets when pressed outside the frames
        parent.bind("<Button-1>", lambda event: event.widget.focus_set())
        self.popup = PopupWindow(parent)

        parent.columnconfigure(index=0, weight=1)
        parent.rowconfigure(index=0, weight=1)
        scroll_frame = ctk.CTkScrollableFrame(parent, fg_color='transparent')
        scroll_frame.grid(column=0, row=0, sticky='nswe')
        scroll_frame.columnconfigure(index=0, weight=1)

        # Organism selection Frame
        outer_species_frame = ctk.CTkFrame(scroll_frame)
        outer_species_frame.grid(column=0, row=0, sticky='we', padx=2, pady=2)
        outer_species_frame.columnconfigure(index=0, weight=1)

        species_frame = ctk.CTkFrame(outer_species_frame, fg_color='transparent')
        species_frame.grid(column=0, row=0, sticky='we', padx=5, pady=5)
        species_frame.columnconfigure(index=2, weight=1)

        ctk.CTkLabel(species_frame, text='Select an organism', font=ctk.CTkFont(weight='bold')).grid(column=0, row=0, padx=5, pady=5)
        self.species = tk.StringVar()
        ctk.CTkComboBox(species_frame, values=['E. coli', 'Custom'], variable=self.species, state='readonly').grid(column=2, row=0, sticky='e', padx=5, pady=5)
        self.cei_model = None
        self.cai_model = None
        self.subspace_model = None
        self.species.trace_add('write', self.load_models)

        # Model frame
        self.model_frame = ctk.CTkFrame(scroll_frame, fg_color='transparent')
        self.model_frame.grid(column=0, row=1, sticky='we')
        self.model_frame.columnconfigure(index=0, weight=1)
        self.model_frame.grid_remove()

        # Genome subspace frame
        outer_gs_frame = ctk.CTkFrame(self.model_frame)
        outer_gs_frame.grid(column=0, row=0, sticky='we', padx=2, pady=2)
        outer_gs_frame.columnconfigure(index=0, weight=1)

        gs_frame = ctk.CTkFrame(outer_gs_frame, fg_color='transparent')
        gs_frame.grid(column=0, row=0, columnspan=1, sticky='we', padx=5, pady=5)
        gs_frame.columnconfigure(index=0, weight=1)
        ctk.CTkLabel(gs_frame, text='Gene Space model', font=ctk.CTkFont(weight='bold')).grid(column=0, row=0, columnspan=2, sticky='w', padx=5, pady=5)

        # Subspace dataset subframe
        gs_path_frame = ctk.CTkFrame(gs_frame, fg_color='transparent')
        gs_path_frame.columnconfigure(index=1, weight=1)
        gs_path_frame.grid(column=0, row=0, sticky='we')

        ctk.CTkLabel(gs_path_frame, text='Path to dataset').grid(column=0, row=0, padx=5, pady=5)
        self.subspace_filename = tk.StringVar()
        ctk.CTkEntry(gs_path_frame, textvariable=self.subspace_filename).grid(column=1, row=0, sticky='we', padx=5, pady=5)
        ctk.CTkButton(gs_path_frame, text='Browse', command=lambda: self.browse(self.subspace_filename)).grid(column=2, row=0, padx=5, pady=5)

        # Everything else in subspace frame
        gs_rest_frame = ctk.CTkFrame(gs_frame, fg_color='transparent')
        gs_rest_frame.grid(column=0, row=1, sticky='we')
        gs_rest_frame.columnconfigure(index=2, weight=1)

        ctk.CTkLabel(gs_rest_frame, text='Fraction of genes inside the subspace').grid(column=0, row=0, padx=5, pady=5)
        self.nu = tk.DoubleVar()
        self.nu.set(0.90)
        ctk.CTkEntry(gs_rest_frame, width=45,textvariable=self.nu).grid(column=1, row=0, padx=5, pady=5)
        ctk.CTkButton(gs_rest_frame, text='Train', command=self.subspace_train).grid(column=3, row=1, sticky='e', padx=5, pady=5)

        # Cei frame
        outer_cei_frame = ctk.CTkFrame(self.model_frame)
        outer_cei_frame.grid(column=0, row=1, sticky='we', padx=2, pady=2)
        outer_cei_frame.columnconfigure(index=0, weight=1)

        cei_frame = ctk.CTkFrame(outer_cei_frame, fg_color='transparent')
        cei_frame.grid(column=0, row=0, sticky='we', padx=5, pady=5)
        cei_frame.columnconfigure(index=1, weight=1)

        ctk.CTkLabel(cei_frame, text='Codon Expression Index model', font=ctk.CTkFont(weight='bold')).grid(column=0, row=0, columnspan=2, sticky='w', padx=5, pady=5)

        ctk.CTkLabel(cei_frame, text='Path to dataset').grid(column=0, row=1, padx=5, pady=5)
        self.cei_dataset_filename = tk.StringVar()
        ctk.CTkEntry(cei_frame, textvariable=self.cei_dataset_filename).grid(column=1, row=1, sticky='we', padx=5, pady=5)
        ctk.CTkButton(cei_frame, text='Browse', command=lambda: self.browse(self.cei_dataset_filename)).grid(column=2, row=1, padx=5, pady=5)
        ctk.CTkButton(cei_frame, text='Train', command=self.expression_train).grid(column=2, row=2, sticky='e', padx=5, pady=5)

        # Input sequence frame
        outer_input_frame = ctk.CTkFrame(scroll_frame)
        outer_input_frame.grid(column=0, row=6, sticky='we', padx=2, pady=2)
        outer_input_frame.columnconfigure(index=0, weight=1)

        input_frame = ctk.CTkFrame(outer_input_frame, fg_color='transparent')
        input_frame.grid(column=0, row=0, sticky='we', padx=5, pady=5)
        input_frame.columnconfigure(index=2, weight=1)

        ctk.CTkLabel(input_frame, text='Input sequence', font=ctk.CTkFont(weight='bold')).grid(column=0, row=0, padx=5, pady=5)

        sequence_types = ['Nucleotide', 'Protein']
        self.sequence_type = tk.StringVar()
        for i in range(len(sequence_types)):
            ctk.CTkRadioButton(input_frame, text=sequence_types[i], variable=self.sequence_type, value=sequence_types[i], radiobutton_height=15, radiobutton_width=15).grid(column = i, row = 1, padx=5, pady=5)
        self.sequence_type.set('Nucleotide')
        self.sequence_type.trace_add('write', self.input_type)

        # Protein sequence input
        self.input_protein_frame = ctk.CTkFrame(input_frame, fg_color='transparent')
        self.input_protein_frame.grid(column=0, row=2, columnspan=3, sticky='we')
        self.input_protein_frame.columnconfigure(index=0, weight=1)

        #self.input_protein_sequence = ctk.CTkTextbox(self.input_protein_frame, height=100, font=ctk.CTkFont(family='Courier'))
        self.input_protein_sequence = PlaceholderTextbox(self.input_protein_frame, placeholder_text='Insert amino acid sequence\nAmino acids should be encoded as single letters', height=100, font=ctk.CTkFont(family='Courier New'))
        self.input_protein_sequence.grid(column=0, row=0, columnspan=5, sticky='we', padx=5, pady=5)
        self.input_protein_frame.grid_remove()

        # Nucleotide sequence input
        self.input_gene_frame = ctk.CTkFrame(input_frame, fg_color='transparent')
        self.input_gene_frame.grid(column=0, row=2, columnspan=3, sticky='we')
        self.input_gene_frame.columnconfigure(index=0, weight=1)

        self.input_gene_sequence = PlaceholderTextbox(self.input_gene_frame, placeholder_text='Insert the nucleotide gene sequence (CDS) in ATGC format', height=100, font=ctk.CTkFont(family='Courier New'))
        #self.input_gene_sequence.insert('end', 'ATGGAGAGCGACGAGAGCGGCCTGCCCGCCATGGAGATCGAGTGCCGCATCACCGGCACCCTGAACGGCGTGGAGTTCGAGCTGGTGGGCGGCGGAGAGGGCACCCCCGAGCAGGGCCGCATGACCAACAAGATGAAGAGCACCAAAGGCGCCCTGACCTTCAGCCCCTACCTGCTGAGCCACGTGATGGGCTACGGCTTCTACCACTTCGGCACCTACCCCAGCGGCTACGAGAACCCCTTCCTGCACGCCATCAACAACGGCGGCTACACCAACACCCGCATCGAGAAGTACGAGGACGGCGGCGTGCTGCACGTGAGCTTCAGCTACCGCTACGAGGCCGGCCGCGTGATCGGCGACTTCAAGGTGATGGGCACCGGCTTCCCCGAGGACAGCGTGATCTTCACCGACAAGATCATCCGCAGCAACGCCACCGTGGAGCACCTGCACCCCATGGGCGATAACGATCTGGATGGCAGCTTCACCCGCACCTTCAGCCTGCGCGACGGCGGCTACTACAGCTCCGTGGTGGACAGCCACATGCACTTCAAGAGCGCCATCCACCCCAGCATCCTGCAGAACGGGGGCCCCATGTTCGCCTTCCGCCGCGTGGAGGAGGATCACAGCAACACCGAGCTGGGCATCGTGGAGTACCAGCACGCCTTCAAGACCCCGGATGCAGATGCCGGTGAAGAATGA')
        self.input_gene_sequence.grid(column=0, row=0, columnspan=5, sticky='we', padx=5, pady=5)
        ctk.CTkButton(self.input_gene_frame, text='Calculate sequence features', command=self.input_parameters).grid(column=0, row=1, sticky='nw', padx=5, pady=5)

        # Input parameters frame
        self.input_param_frame = ctk.CTkFrame(self.input_gene_frame, fg_color='transparent')
        self.input_param_frame.grid(column=1, row=1)
        self.input_expression = tk.StringVar()
        self.input_cai = tk.StringVar()
        self.input_distance = tk.StringVar()
        self.input_cd = tk.StringVar()
        self.input_gc = tk.StringVar()
        ctk.CTkLabel(self.input_param_frame, textvariable=self.input_expression).grid(column=0, row=0, sticky='w', padx=5, pady=5)
        ctk.CTkLabel(self.input_param_frame, textvariable=self.input_cai).grid(column=0, row=1, sticky='w', padx=5, pady=5)
        ctk.CTkLabel(self.input_param_frame, textvariable=self.input_distance).grid(column=0, row=2, sticky='w', padx=5, pady=5)
        ctk.CTkLabel(self.input_param_frame, textvariable=self.input_cd).grid(column=0, row=3, sticky='w', padx=5, pady=5)
        ctk.CTkLabel(self.input_param_frame, textvariable=self.input_gc).grid(column=0, row=4, sticky='w', padx=5, pady=5)
        ctk.CTkButton(self.input_param_frame, text='Show on Graph', command=self.expression_graph).grid(column = 1, row=0, padx=5, pady=5)
        ctk.CTkButton(self.input_param_frame, text='Show on Graph', command=self.cai_graph).grid(column = 1, row=1, padx=5, pady=5)
        ctk.CTkButton(self.input_param_frame, text='Show on Graph', command=self.subspace_graph).grid(column = 1, row=2, padx=5, pady=5)
        self.input_param_frame.grid_remove()

        # Optimiser settings frame
        outer_settings_frame = ctk.CTkFrame(scroll_frame)
        outer_settings_frame.grid(column=0, row=7, sticky='we', padx=2, pady=2)
        outer_settings_frame.columnconfigure(index=0, weight=1)

        self.settings_frame = ctk.CTkFrame(outer_settings_frame, fg_color='transparent')
        self.settings_frame.grid(column=0, row=0, sticky='we', padx=5, pady=5)
        self.settings_frame.columnconfigure(index=2, weight=1)
        ctk.CTkLabel(self.settings_frame, text='Optimisation settings', font=ctk.CTkFont(weight='bold')).grid(column=0, row=0, sticky='w', padx=5, pady=5)

        # Expression parameters
        self.expression_switch = tk.BooleanVar()
        expression_switch = ctk.CTkSwitch(self.settings_frame, text='Expression', variable=self.expression_switch, command=self.settings_handler)
        expression_switch.grid(column=0, row=1, sticky='w', padx=5, pady=5)
        ToolTip(expression_switch, text='Desired expression level - number of protein copies per cell\n\nWe recommend range from 10 to 100,000')

        self.target_expression = tk.IntVar()
        self.target_expression_spinbox = ctk.CTkEntry(self.settings_frame, width=50, textvariable=self.target_expression)
        self.target_expression_spinbox.grid(column=1, row=1, padx=5, pady=3)
        self.target_expression_spinbox.grid_remove()
        self.target_expression.set(10)

        self.expression_priority_label = ctk.CTkLabel(self.settings_frame, text='Parameter weight')
        self.expression_priority_label.grid(column=3, row=1, padx=5, pady=3)
        self.expression_priority_label.grid_remove()

        self.expression_priority = tk.IntVar()
        self.expression_priority_spinbox = ctk.CTkEntry(self.settings_frame, width=30, textvariable=self.expression_priority)
        self.expression_priority_spinbox.grid(column=4, row=1, sticky='w', padx=5, pady=3)
        self.expression_priority_spinbox.grid_remove()

        # Subspace distance
        self.subspace_switch = tk.BooleanVar()
        subspace_switch = ctk.CTkSwitch(self.settings_frame, text='Species optimisation', variable=self.subspace_switch, command=self.settings_handler)
        subspace_switch.grid(column=0, row=2, sticky='w', padx=5, pady=5)
        ToolTip(subspace_switch, text='For E.coli we recommend selecting 0.002 as a median value from the graph. A positive number corresponding to a position within the so-called Gene Subspace. The values for the organism’s genes are shown on the Graph.')

        self.target_distance = tk.DoubleVar()
        self.target_distance_spinbox = ctk.CTkEntry(self.settings_frame, width=50, textvariable=self.target_distance)
        self.target_distance_spinbox.grid(column=1, row=2, padx=5, pady=3)
        self.target_distance_spinbox.grid_remove()

        self.subspace_priority_label = ctk.CTkLabel(self.settings_frame, text='Parameter weight')
        self.subspace_priority_label.grid(column=3, row=2, padx=5, pady=3)
        self.subspace_priority_label.grid_remove()

        self.subspace_priority = tk.IntVar()
        self.subspace_priority_spinbox = ctk.CTkEntry(self.settings_frame, width=30, textvariable=self.subspace_priority)
        self.subspace_priority_spinbox.grid(column=4, row=2, sticky='w', padx=5, pady=3)
        self.subspace_priority_spinbox.grid_remove()

        # Center distance parameters
        self.center_switch = tk.BooleanVar()
        center_switch = ctk.CTkSwitch(self.settings_frame, text='Codon usage irregularity', variable=self.center_switch, command=self.settings_handler)
        center_switch.grid(column=0, row=3, sticky='w', padx=5, pady=5)
        ToolTip(center_switch, text='Simulated nucleotide sequence codon usage evenness: 0 indicates a sequence encoded by a single codon; 1 indicates a sequence in which all codons are used in equal proportions.')

        self.target_center = tk.DoubleVar()
        self.target_center_spinbox = ctk.CTkEntry(self.settings_frame, width=50, textvariable=self.target_center)
        self.target_center_spinbox.grid(column=1, row=3, padx=5, pady=3)
        self.target_center_spinbox.grid_remove()

        self.center_priority_label = ctk.CTkLabel(self.settings_frame, text='Parameter weight')
        self.center_priority_label.grid(column=3, row=3, padx=5, pady=3)
        self.center_priority_label.grid_remove()

        self.center_priority = tk.IntVar()
        self.center_priority_spinbox = ctk.CTkEntry(self.settings_frame, width=30, textvariable=self.center_priority)
        self.center_priority_spinbox.grid(column=4, row=3, sticky='w', padx=5, pady=3)
        self.center_priority_spinbox.grid_remove()

        # GC parameters
        self.gc_switch = tk.BooleanVar()
        gc_switch = ctk.CTkSwitch(self.settings_frame, text='GC content', variable=self.gc_switch, command=self.settings_handler)
        gc_switch.grid(column=0, row=4, sticky='w', padx=5, pady=5)
        ToolTip(gc_switch, text='GC content of the simulated nucleotide sequence (50 corresponds to an average level). Note that your selection may conflict with the “Species optimisation” option.')

        self.target_gc = tk.IntVar()
        self.target_gc_spinbox = ctk.CTkEntry(self.settings_frame, width=50, textvariable=self.target_gc)
        self.target_gc_spinbox.grid(column=1, row=4, padx=5, pady=3)
        self.target_gc_spinbox.grid_remove()

        self.gc_priority_label = ctk.CTkLabel(self.settings_frame, text='Parameter weight')
        self.gc_priority_label.grid(column=3, row=4, padx=5, pady=3)
        self.gc_priority_label.grid_remove()

        self.gc_priority = tk.IntVar()
        self.gc_priority_spinbox = ctk.CTkEntry(self.settings_frame, width=30, textvariable=self.gc_priority)
        self.gc_priority_spinbox.grid(column=4, row=4, sticky='w', padx=5, pady=3)
        self.gc_priority_spinbox.grid_remove()

        # Restriction sites
        self.exclusion_switch = tk.BooleanVar()
        exclusion_switch = ctk.CTkSwitch(self.settings_frame, text='Excluded sites', variable=self.exclusion_switch, command=self.settings_handler)
        exclusion_switch.grid(column=0, row=5, sticky='w', padx=5, pady=5)
        ToolTip(exclusion_switch, text='Add oligonucleotides to exclude from the simulated optimised sequence. Add oligonucleotides to exclude from the simulated optimised sequence. One sequence per row.')

        self.exclusion_frame = ctk.CTkFrame(self.settings_frame, fg_color='transparent')
        self.exclusion_frame.grid(column=0, row=6, columnspan=5, sticky='we')
        self.exclusion_frame.grid_remove()
        #ctk.CTkLabel(self.exclusion_frame, text='Sites to be excluded from optimised sequence:').grid(column=0, row=0, sticky='w', padx=5, pady=5)
        self.exclusion_sites = PlaceholderTextbox(self.exclusion_frame, placeholder_text='Example:\nAAA\nATGGTA', height=75)
        self.exclusion_sites.grid(column=0, row=1, sticky='we', padx=5, pady=5)

        # Advanced
        self.advanced_switch = tk.BooleanVar()
        advanced_switch = ctk.CTkSwitch(self.settings_frame, text='Advanced settings', variable=self.advanced_switch, command=self.settings_handler)
        advanced_switch.grid(column=0, row=7, sticky='w', padx=5, pady=5)
        ToolTip(advanced_switch, text='Change parameters of the optimisation algorithm')

        self.advanced_frame = ctk.CTkFrame(self.settings_frame, fg_color='transparent')
        self.advanced_frame.grid(column=0, row=8, columnspan=6, sticky='we')
        self.advanced_frame.columnconfigure(index=0, weight=1)
        self.advanced_frame.columnconfigure(index=1, weight=1)
        self.advanced_frame.columnconfigure(index=2, weight=1)

        ctk.CTkLabel(self.advanced_frame, text='Seed size').grid(column=0, row=0, padx=5, pady=5)
        self.set_size = tk.IntVar()
        self.set_size.set(1000)
        ctk.CTkEntry(self.advanced_frame, width=50, textvariable=self.set_size).grid(column=0, row=1, padx=5, pady=5)

        ctk.CTkLabel(self.advanced_frame, text='Number of sequences\ngenerated at each step').grid(column=1, row=0, padx=5, pady=5)
        self.n_children = tk.IntVar()
        self.n_children.set(10)
        ctk.CTkEntry(self.advanced_frame, width=50, textvariable=self.n_children).grid(column=1, row=1, padx=5, pady=5)

        ctk.CTkLabel(self.advanced_frame, text='Number of iterations without\nimprovement before stop').grid(column=2, row=0, padx=5, pady=5)
        self.max_iterations = tk.IntVar()
        self.max_iterations.set(300)
        ctk.CTkEntry(self.advanced_frame, width=50, textvariable=self.max_iterations).grid(column=2, row=1, padx=5, pady=5)
        self.advanced_frame.grid_remove()

        ctk.CTkButton(self.settings_frame, text='Clear all', command=self.clear_all).grid(column=0, row=9, sticky='w', padx=5, pady=5)
        ctk.CTkButton(self.settings_frame, text='Optimise sequence', command=self.optimize).grid(column=4, row=9, sticky='e', padx=5, pady=5)

        # Output sequence frame
        self.outer_output_frame = ctk.CTkFrame(scroll_frame)
        self.outer_output_frame.grid(column=0, row=8, sticky='we', padx=2, pady=2)
        self.outer_output_frame.columnconfigure(index=0, weight=1)

        output_frame = ctk.CTkFrame(self.outer_output_frame, fg_color='transparent')
        output_frame.grid(column=0, row=0, sticky='we', padx=5, pady=5)
        output_frame.columnconfigure(index=0, weight=1)
        ctk.CTkLabel(output_frame, text='Optimised sequence', font=ctk.CTkFont(weight='bold')).grid(column=0, row=0, sticky='w', padx=5, pady=5)

        self.output_sequence = ctk.CTkTextbox(output_frame, height=100, takefocus=0, font=ctk.CTkFont(family='Courier New'))
        self.output_sequence.grid(column=0, row=1, columnspan=5, sticky='we', padx=5, pady=5)
        self.output_sequence.configure(state='disabled')

        self.result_copy = ctk.CTkButton(output_frame, text='Copy sequence', command=self.copy_result)
        self.result_copy.grid(column=0, row=2, sticky='nw', padx=5, pady=5)
        self.result_copy.grid_remove()

        #ctk.CTkButton(output_frame, text='Clear all', command=self.clear_all).grid(column=0, row=3, sticky='sw', padx=5, pady=5)

        # Output parameters frame
        self.output_param_frame = ctk.CTkFrame(output_frame, fg_color='transparent')
        self.output_param_frame.grid(column=1, row=2, rowspan=2)
        self.output_expression = tk.StringVar()
        self.output_cai = tk.StringVar()
        self.output_distance = tk.StringVar()
        self.output_cd = tk.StringVar()
        self.output_gc = tk.StringVar()
        ctk.CTkLabel(self.output_param_frame, textvariable=self.output_expression).grid(column=1, row=0, sticky='w', padx=5, pady=5)
        ctk.CTkLabel(self.output_param_frame, textvariable=self.output_cai).grid(column=1, row=1, sticky='w', padx=5, pady=5)
        ctk.CTkLabel(self.output_param_frame, textvariable=self.output_distance).grid(column=1, row=2, sticky='w', padx=5, pady=5)
        ctk.CTkLabel(self.output_param_frame, textvariable=self.output_cd).grid(column=1, row=3, sticky='w', padx=5, pady=5)
        ctk.CTkLabel(self.output_param_frame, textvariable=self.output_gc).grid(column=1, row=4, sticky='w', padx=5, pady=5)
        ctk.CTkButton(self.output_param_frame, text='Show on Graph', command=self.expression_graph).grid(column=2, row=0, padx=5, pady=5)
        ctk.CTkButton(self.output_param_frame, text='Show on Graph', command=self.cai_graph).grid(column=2, row=1, padx=5, pady=5)
        ctk.CTkButton(self.output_param_frame, text='Show on Graph', command=self.subspace_graph).grid(column=2, row=2, padx=5, pady=5)
        self.output_param_frame.grid_remove()
        self.outer_output_frame.grid_remove()

    def copy_result(self):
        self.parent.clipboard_clear()
        self.parent.clipboard_append(self.output_sequence.get('1.0', 'end-1c'))
        self.parent.update()

    def clear_all(self):
        self.input_gene_sequence.delete('1.0', 'end')
        self.input_protein_sequence.delete('1.0', 'end')
        self.output_sequence.configure(state='normal')
        self.output_sequence.delete('1.0', 'end')
        self.output_sequence.configure(state='disabled')

        self.clear_parameter_frames()
        self.outer_output_frame.grid_remove()

        self.expression_switch.set(False)
        self.target_expression.set(10)
        self.target_expression_spinbox.grid_remove()
        self.expression_priority_spinbox.grid_remove()
        self.expression_priority_label.grid_remove()
        self.expression_priority.set(0)

        self.subspace_switch.set(False)
        self.target_distance.set(0)
        self.target_distance_spinbox.grid_remove()
        self.subspace_priority_spinbox.grid_remove()
        self.subspace_priority_label.grid_remove()
        self.subspace_priority.set(0)

        self.center_switch.set(False)
        self.target_center.set(0)
        self.target_center_spinbox.grid_remove()
        self.center_priority_spinbox.grid_remove()
        self.center_priority_label.grid_remove()
        self.center_priority.set(0)

        self.gc_switch.set(False)
        self.target_gc.set(0)
        self.target_gc_spinbox.grid_remove()
        self.gc_priority_spinbox.grid_remove()
        self.gc_priority_label.grid_remove()
        self.gc_priority.set(0)

        self.exclusion_switch.set(False)
        self.exclusion_sites.delete('1.0', 'end')

        self.advanced_switch.set(False)
        self.set_size.set(1000)
        self.n_children.set(10)
        self.max_iterations.set(300)

    def settings_handler(self):
        if self.expression_switch.get():
            self.target_expression_spinbox.grid()
            self.expression_priority_spinbox.grid()
            self.expression_priority_label.grid()
            self.expression_priority.set(1)

        else:
            self.target_expression_spinbox.grid_remove()
            self.expression_priority_spinbox.grid_remove()
            self.expression_priority_label.grid_remove()
            self.expression_priority.set(0)

        if self.subspace_switch.get():
            self.target_distance_spinbox.grid()
            self.subspace_priority_spinbox.grid()
            self.subspace_priority_label.grid()
            self.subspace_priority.set(1)
        else:
            self.target_distance_spinbox.grid_remove()
            self.subspace_priority_spinbox.grid_remove()
            self.subspace_priority_label.grid_remove()
            self.subspace_priority.set(0)

        if self.center_switch.get():
            self.target_center_spinbox.grid()
            self.center_priority_spinbox.grid()
            self.center_priority_label.grid()
            self.center_priority.set(1)
        else:
            self.target_center_spinbox.grid_remove()
            self.center_priority_spinbox.grid_remove()
            self.center_priority_label.grid_remove()
            self.center_priority.set(0)

        if self.gc_switch.get():
            self.target_gc_spinbox.grid()
            self.gc_priority_spinbox.grid()
            self.gc_priority_label.grid()
            self.gc_priority.set(1)
        else:
            self.target_gc_spinbox.grid_remove()
            self.gc_priority_spinbox.grid_remove()
            self.gc_priority_label.grid_remove()
            self.gc_priority.set(0)

        if self.exclusion_switch.get():
            self.exclusion_frame.grid()
        else:
            self.exclusion_frame.grid_remove()

        if self.advanced_switch.get():
            self.advanced_frame.grid()
        else:
            self.advanced_frame.grid_remove()

        # Force geometry calculation and redraw
        self.settings_frame.update_idletasks()
        self.parent.update_idletasks()

    def input_type(self, var, index, mode):
        if self.sequence_type.get() == 'Nucleotide':
            self.input_protein_frame.grid_remove()
            self.input_gene_frame.grid()
        else:
            self.input_gene_frame.grid_remove()
            self.input_protein_frame.grid()

    def expression_graph(self):
        graph_window = ctk.CTkToplevel(self.parent)
        graph_window.title(self.species.get() + ' Expression Histogram')
        graph_window.geometry("700x500")
        graph_window.columnconfigure(index=0, weight=1)
        graph_window.rowconfigure(index=0, weight=1)

        fig = plt.figure()
        plt.hist(self.cei_model.expression, bins=50)
        if self.input_expression.get() != '':
            plt.axvline(x=self.cei_model.predict(read_sequence(self.input_gene_sequence.get('1.0', 'end-1c'))), color='grey')
        if self.output_expression.get() != '':
            plt.axvline(x=self.cei_model.predict(self.output_sequence.get('1.0', 'end-1c')), color='red')
        plt.xlim(0, None)
        plt.xticks([i for i in range(0, 13, 2)], [str(int(exp(i) - 1)) for i in range(0, 13, 2)])
        plt.xlabel('Protein copies per cell')
        plt.yticks([])
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky='nswe')

    def cai_graph(self):
        graph_window = ctk.CTkToplevel(self.parent)
        graph_window.title(self.species.get() + ' CAI Histogram')
        graph_window.geometry("700x500")
        graph_window.columnconfigure(index=0, weight=1)
        graph_window.rowconfigure(index=0, weight=1)

        fig = plt.figure()
        plt.hist(self.cai_model.predictions, bins=50)
        if self.input_cai.get() != '':
            plt.axvline(x=self.cai_model.predict(read_sequence(self.input_gene_sequence.get('1.0', 'end-1c'))), color='grey')
        if self.output_cai.get() != '':
            plt.axvline(x=self.cai_model.predict(self.output_sequence.get('1.0', 'end-1c')), color='red')
        plt.xlim(0, None)
        plt.yticks([i / 10 for i in range(0, 11, 1)], [str(i / 10) for i in range(0, 11, 1)])
        plt.xlabel('Codon Adaptation Index value')
        plt.yticks([])
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky='nswe')

    def subspace_graph(self):
        graph_window = ctk.CTkToplevel(self.parent)
        graph_window.title(self.species.get() + ' Species Optimisation Histogram')
        graph_window.geometry("700x500")
        graph_window.columnconfigure(index=0, weight=1)
        graph_window.rowconfigure(index=0, weight=1)

        fig = plt.figure()
        plt.hist(self.subspace_model.distances, bins=50)
        if self.input_distance.get() != '':
            plt.axvline(x=self.subspace_model.distance(read_sequence(self.input_gene_sequence.get('1.0', 'end-1c'))), color='grey')
        if self.output_distance.get() != '':
            plt.axvline(x=self.subspace_model.distance(self.output_sequence.get('1.0', 'end-1c')), color='red')
        #plt.xlim(0, None)
        #plt.xticks([i for i in range(0, 13, 2)], [str(int(exp(i) - 1)) for i in range(0, 13, 2)])
        plt.xlabel('Distance from the edge of the Genome Subspace')
        plt.yticks([])
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky='nswe')

    def load_models(self, var, index, mode):
        if self.species.get() == 'Custom':
            self.cei_model = None
            self.cai_model = None
            self.subspace_model = None
            self.clear_parameter_frames()
            self.model_frame.grid()
        else:
            self.model_frame.grid_remove()
            self.clear_parameter_frames()
            with open(resource_path('trained_models/511145_cei.pkl'), 'rb') as file: self.cei_model = pickle.load(file)
            with open(resource_path('trained_models/511145_cai.pkl'), 'rb') as file: self.cai_model = pickle.load(file)
            with open(resource_path('trained_models/511145_sub.pkl'), 'rb') as file: self.subspace_model = pickle.load(file)

    def clear_parameter_frames(self):
        self.input_expression.set('')
        self.input_cai.set('')
        self.input_distance.set('')
        self.input_cd.set('')
        self.input_gc.set('')
        self.input_param_frame.grid_remove()
        self.clear_output_parameters()

    def clear_output_parameters(self):
        self.output_expression.set('')
        self.output_cai.set('')
        self.output_distance.set('')
        self.output_cd.set('')
        self.output_gc.set('')
        self.output_param_frame.grid_remove()
        self.result_copy.grid_remove()

    def browse(self, filepath):
        self.parent.focus()
        filepath.set(filedialog.askopenfilename())

    def subspace_train(self):
        self.parent.focus()
        self.subspace_model = GeneSpace.CodonPairSubspace(self.subspace_filename.get(), nu=1-self.nu.get())

    def expression_train(self):
        self.parent.focus()
        self.cei_model = CodonExpressionIndex.CodonExpressionIndex(self.cei_dataset_filename.get())
        self.cai_model = CodonExpressionIndex.CodonAdaptationIndex(self.cei_dataset_filename.get())

    def input_parameters(self):
        self.parent.focus()
        error = ''
        gene = read_sequence(self.input_gene_sequence.get('1.0', 'end-1c'))
        if gene == '':
            error = 'No input sequence'
        elif len(gene) % 3 != 0:
            error = 'Sequence length in not a multiple of 3'
        elif set([i for i in gene]) - {'A', 'T', 'G', 'C'}:
            error = 'Sequence contains characters other than ATGC'

        if self.subspace_model is None:
            error = 'Select model organism'

        if error != '':
            self.popup.show(error)

        else:
            cei_score = round(self.cei_model.predict(gene), 2)
            ppc = int(exp(cei_score) - 1)
            gc_content = int((gene.count('G') + gene.count('C')) / len(gene) * 100)
            cai_score = round(self.cai_model.predict(gene), 2)
            subspace_distance = round(self.subspace_model.distance(gene), 4)
            center_distance = int(self.subspace_model.center_distance(gene) * 100)
            self.input_expression.set('Predicted Expression = ' + str(ppc) + ' ppm')
            self.input_cai.set('Codon Adaptation Index = ' + str(cai_score))
            self.input_distance.set('Species Optimisation = ' + str(subspace_distance))
            self.input_cd.set('Codon Usage Irregularity = ' + str(center_distance) + '%')
            self.input_gc.set('GC Content = ' + str(gc_content) + '%')
            self.input_param_frame.grid()

    def read_exclusion_sites(self):
        data = self.exclusion_sites.get('1.0', 'end-1c')
        sites = []
        for line in data.split('\n'):
            site = line.replace(' ', '').upper()
            if site != '':
                sites.append()
        return sites

    def optimize(self):
        self.parent.focus()
        self.clear_output_parameters()
        error = ''
        if self.sequence_type.get() == 'Nucleotide':
            gene = read_sequence(self.input_gene_sequence.get('1.0', 'end-1c'))
            if gene == '':
                error = 'No input sequence'
            elif len(gene) % 3 != 0:
                error = 'Sequence length in not a multiple of 3'
            elif set([i for i in gene]) - {'A', 'T', 'G', 'C'}:
                error = 'Sequence contains characters other than ATGC'
        else:
            protein = read_sequence(self.input_protein_sequence.get('1.0', 'end-1c'))
            if protein == '':
                error = 'No input sequence'
            elif set([i for i in protein]) - {'A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'Y'}:
                error = 'Sequence contains non standard amino acids'
            else:
                gene = translate(protein)

        if self.expression_priority.get() == self.subspace_priority.get() == self.center_priority.get() == self.gc_priority.get() == 0:
            error = 'Select at least one optimisation parameter'

        if self.subspace_model is None:
            error = 'Select model organism'

        if error != '':
            self.popup.show(error)

        else:
            if self.exclusion_switch.get():
                exclusion_sites = self.read_exclusion_sites()
            else:
                exclusion_sites = []

            optimizer = Optimizer(expression_model=self.cei_model, subspace_model=self.subspace_model, input_sequence=gene, set_size=self.set_size.get(), expression_priority=self.expression_priority.get(), subspace_priority=self.subspace_priority.get(), center_priority=self.center_priority.get(), gc_priority=self.gc_priority.get(), n_children=self.n_children.get(), max_iterations=self.max_iterations.get(), restriction_sites=exclusion_sites)
            #adjusted = optimizer.optimize(target_score=log(self.target_expression.get() + 1), target_distance=self.target_distance.get(), target_center=self.target_center.get() / 100, target_gc=self.target_gc.get() / 100)

            worker_state = run_in_process(self.parent, optimizer.optimize, target_score=log(self.target_expression.get() + 1), target_distance=self.target_distance.get(), target_center=self.target_center.get() / 100, target_gc=self.target_gc.get() / 100)
            if worker_state['stopped']:
                return
            elif worker_state['error']:
                self.popup.show(worker_state['error'])
            else:
                adjusted = worker_state['result']

                self.output_sequence.configure(state='normal')
                self.output_sequence.delete('1.0', 'end')
                self.output_sequence.insert('end', adjusted.strip())
                self.output_sequence.configure(state='disabled')

                cei_score = round(self.cei_model.predict(adjusted), 2)
                ppc = int(exp(cei_score) - 1)
                gc_content = int((adjusted.count('G') + adjusted.count('C')) / len(adjusted) * 100)
                cai_score = round(self.cai_model.predict(adjusted), 2)
                subspace_distance = round(self.subspace_model.distance(adjusted), 4)
                center_distance = int(self.subspace_model.center_distance(adjusted) * 100)
                self.output_expression.set('Predicted Expression = ' + str(ppc) + ' ppm')
                self.output_cai.set('Codon Adaptation Index = ' + str(cai_score))
                self.output_distance.set('Species Optimisation = ' + str(subspace_distance))
                self.output_cd.set('Codon Usage Irregularity = ' + str(center_distance) + '%')
                self.output_gc.set('GC Content = ' + str(gc_content) + '%')
                self.outer_output_frame.grid()
                self.output_param_frame.grid()
                self.result_copy.grid()


def read_sequence(input_sequence):
    sequence = ''
    for line in input_sequence.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        if line and line[0] != '>':
            sequence += line
    return sequence.replace(' ', '').replace('	', '').upper()


def close_window():
    plt.close()
    root.destroy()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    if sys.platform.startswith("win"):
        set_window_icon(root)
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", close_window)
    root.mainloop()
