import os
import sys
import time
import queue
import threading
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw
import pystray

from translator import get_text_under_cursor, HoverTranslator
from tooltip import FloatingTooltip

# Thread-safe queue for UI actions
ui_queue = queue.Queue()

# Global settings
settings = {
    "enabled": True,
    "hover_delay": 0.05,     # Default to 50ms for instant hover response
    "target_lang": "en",
    "last_processed_text": ""
}

# Threads controller
running = True
current_hover_id = 0  # Global hover session counter

def translation_worker(hover_id, x, y, target_lang, translator_instance):
    global current_hover_id
    if current_hover_id != hover_id:
        return
        
    import comtypes
    # Initialize COM for this background thread
    comtypes.CoInitialize()
    try:
        from translator import get_text_under_cursor_at
        text = get_text_under_cursor_at(x, y)
        
        if current_hover_id != hover_id:
            return
            
        if not text:
            ui_queue.put(("hide",))
            return
            
        text_clean = text.strip()
        if not text_clean:
            ui_queue.put(("hide",))
            return
            
        # Check if text is same as last processed text
        if text_clean == settings["last_processed_text"]:
            return
            
        translated, lang = translator_instance.translate(text_clean, target_lang)
        
        if current_hover_id != hover_id:
            return
            
        if translated:
            ui_queue.put(("show", translated, lang, x, y))
            settings["last_processed_text"] = text_clean
        else:
            ui_queue.put(("hide",))
            
    except Exception as e:
        print(f"Worker Exception: {e}")
    finally:
        # Uninitialize COM for this background thread
        comtypes.CoUninitialize()

def generate_tray_icon():
    """Generates a sleek 64x64 pixels icon dynamically using Pillow."""
    img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw a modern circular/rounded gradient-like blue background
    draw.rounded_rectangle([4, 4, 60, 60], radius=16, fill=(26, 115, 232, 255))
    # Draw a clean white letter "T" in the center using lines
    draw.line([20, 20, 44, 20], fill=(255, 255, 255, 255), width=5)
    draw.line([32, 20, 32, 48], fill=(255, 255, 255, 255), width=5)
    return img

class HoverTranslatorApp:
    def __init__(self):
        # Configure CustomTkinter appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize main window
        self.root = ctk.CTk()
        self.root.title("Hover Translator")
        self.root.geometry("420x420")
        self.root.resizable(False, False)
        
        # Handle close event (minimize to tray instead of exiting)
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
        # Initialize translator and tooltip components
        self.translator = HoverTranslator()
        self.tooltip = FloatingTooltip()
        
        # Build UI layout
        self.build_ui()
        
        # Start queue processing
        self.process_queue()
        
        # Setup system tray icon
        self.setup_tray()
        
        # Start hover thread
        self.start_hover_thread()
        
    def build_ui(self):
        """Creates the settings panel UI with modern CustomTkinter widgets."""
        # Main container with padding
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=15)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title Header
        self.title_label = ctk.CTkLabel(
            self.main_frame, 
            text="Hover Translator", 
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold")
        )
        self.title_label.pack(pady=(20, 5))
        
        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            self.main_frame, 
            text="Hover over text to translate instantly", 
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#8AB4F8"
        )
        self.subtitle_label.pack(pady=(0, 20))
        
        # Active State Switch
        self.enabled_switch = ctk.CTkSwitch(
            self.main_frame, 
            text="Enable Translation Hover", 
            command=self.toggle_active,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.enabled_switch.select()
        self.enabled_switch.pack(pady=10)
        
        # Hover Delay Slider Frame
        self.slider_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.slider_frame.pack(fill=tk.X, padx=30, pady=10)
        
        self.delay_label = ctk.CTkLabel(
            self.slider_frame, 
            text=f"Hover Delay: {settings['hover_delay']:.2f}s", 
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.delay_label.pack(side=tk.LEFT)
        
        self.delay_slider = ctk.CTkSlider(
            self.slider_frame, 
            from_=0.01, 
            to=1.0, 
            number_of_steps=99,
            command=self.update_delay
        )
        self.delay_slider.set(settings["hover_delay"])
        self.delay_slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(15, 0))
        
        # Target Language Selection Frame
        self.lang_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.lang_frame.pack(fill=tk.X, padx=30, pady=10)
        
        self.lang_label = ctk.CTkLabel(
            self.lang_frame, 
            text="Translate to:", 
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.lang_label.pack(side=tk.LEFT)
        
        self.lang_switch = ctk.CTkSegmentedButton(
            self.lang_frame,
            values=["English", "Hindi"],
            command=self.change_target_lang
        )
        current_sel = "English" if settings["target_lang"] == "en" else "Hindi"
        self.lang_switch.set(current_sel)
        self.lang_switch.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(15, 0))
        
        # Tray Button / Info Footer
        self.tray_button = ctk.CTkButton(
            self.main_frame, 
            text="Minimize to System Tray", 
            command=self.minimize_to_tray,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=35
        )
        self.tray_button.pack(pady=(20, 10))
        
        self.status_footer = ctk.CTkLabel(
            self.main_frame, 
            text="App running in background", 
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="gray"
        )
        self.status_footer.pack()
        
    def change_target_lang(self, value):
        settings["target_lang"] = "en" if value == "English" else "hi"
        settings["last_processed_text"] = ""

    def toggle_active(self):
        settings["enabled"] = self.enabled_switch.get() == 1
        if not settings["enabled"]:
            ui_queue.put(("hide",))

    def update_delay(self, value):
        settings["hover_delay"] = round(value, 2)
        self.delay_label.configure(text=f"Hover Delay: {settings['hover_delay']:.2f}s")

    def minimize_to_tray(self):
        self.root.withdraw()
        # Notify the user via OS notification if possible
        try:
            self.tray_icon.notify("Hover Translator minimized to system tray. Hover over text to translate.", "Running in background")
        except Exception:
            pass

    def restore_from_tray(self):
        self.root.after(0, self.root.deiconify)
        self.root.after(0, self.root.focus_force)

    def quit_app(self):
        global running
        running = False
        self.tray_icon.stop()
        self.tooltip.destroy()
        self.root.destroy()
        sys.exit(0)

    def setup_tray(self):
        """Sets up the system tray icon and menu."""
        menu = pystray.Menu(
            pystray.MenuItem("Open Settings", self.restore_from_tray, default=True),
            pystray.MenuItem("Enable / Disable", self.toggle_tray_active, checked=lambda item: settings["enabled"]),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.quit_app)
        )
        self.tray_icon = pystray.Icon(
            "hover_translator", 
            generate_tray_icon(), 
            "Hover Translator", 
            menu
        )
        # Run the tray icon loop in a background thread
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def toggle_tray_active(self):
        settings["enabled"] = not settings["enabled"]
        self.root.after(0, lambda: self.enabled_switch.toggle() if hasattr(self, 'enabled_switch') else None)
        if not settings["enabled"]:
            ui_queue.put(("hide",))

    def process_queue(self):
        """Polls the queue for actions and updates the tooltip UI on the main thread."""
        try:
            while True:
                item = ui_queue.get_nowait()
                action = item[0]
                if action == "show":
                    _, text, lang, x, y = item
                    self.tooltip.show(text, lang, x, y)
                elif action == "hide":
                    self.tooltip.hide()
        except queue.Empty:
            pass
        self.root.after(10, self.process_queue)

    def start_hover_thread(self):
        """Launches the background hover detection loop in a daemon thread."""
        threading.Thread(target=self.hover_detection_loop, daemon=True).start()

    def hover_detection_loop(self):
        """Background thread loop tracking cursor coordinate stillness and spawning translation workers."""
        global current_hover_id
        import ctypes
        
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            
        def get_pos():
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            return pt.x, pt.y

        last_x, last_y = get_pos()
        hover_start_time = time.time()
        is_hovering = False

        # Pre-load automation DLL
        try:
            from translator import load_uiautomation
            load_uiautomation()
        except Exception as e:
            print(f"Pre-load error: {e}")

        while running:
            time.sleep(0.03)  # Tick rate 30ms for extreme snappiness
            
            if not settings["enabled"]:
                continue
                
            try:
                x, y = get_pos()
            except Exception:
                continue

            # Check if mouse has moved beyond jitter threshold (2px)
            if abs(x - last_x) > 2 or abs(y - last_y) > 2:
                # Mouse is moving, cancel any active translations and hide tooltip
                last_x, last_y = x, y
                hover_start_time = time.time()
                current_hover_id += 1  # Increments session ID to abort running threads
                
                # Clear last processed text to allow re-translating when hovering back
                settings["last_processed_text"] = ""
                
                if is_hovering:
                    ui_queue.put(("hide",))
                    is_hovering = False
            else:
                # Mouse is still. If hover time elapsed and not yet triggered
                delay_threshold = settings["hover_delay"]
                if not is_hovering and (time.time() - hover_start_time >= delay_threshold):
                    is_hovering = True
                    current_hover_id += 1
                    
                    # Spawn worker thread to extract and translate text asynchronously
                    t = threading.Thread(
                        target=translation_worker,
                        args=(current_hover_id, x, y, settings["target_lang"], self.translator),
                        daemon=True
                    )
                    t.start()

if __name__ == "__main__":
    app = HoverTranslatorApp()
    app.root.mainloop()
