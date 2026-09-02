import tkinter as tk

class FloatingTooltip:
    def __init__(self):
        self.root = None
        self.fade_job = None
        
    def _create_window(self):
        """Creates the borderless, topmost tooltip window."""
        self.root = tk.Toplevel()
        # Remove window decoration
        self.root.overrideredirect(True)
        # Keep on top
        self.root.attributes("-topmost", True)
        # Avoid focus
        self.root.attributes("-toolwindow", True)
        # Set background to dark gray
        self.root.configure(bg="#1A1A1A", bd=0)
        
        # Outer frame for border styling (sleek glassmorphic border)
        self.frame = tk.Frame(self.root, bg="#1A1A1A", highlightbackground="#3A3F4B", highlightthickness=1)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Main translated text label
        self.text_label = tk.Label(
            self.frame, 
            text="", 
            font=("Segoe UI", 10), 
            fg="#FFFFFF", 
            bg="#1A1A1A", 
            wraplength=350, 
            justify=tk.LEFT,
            anchor="w"
        )
        self.text_label.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        
        # Start transparent
        self.root.attributes("-alpha", 0.0)
        
    def show(self, text, detected_lang, x, y):
        """Displays the tooltip at the cursor position (x, y) with fade-in."""
        # Cancel any active fade job
        if self.fade_job:
            try:
                self.root.after_cancel(self.fade_job)
            except Exception:
                pass
            self.fade_job = None
            
        if not self.root or not self.root.winfo_exists():
            self._create_window()
            
        # Update text with language prefixed in brackets
        formatted_text = f"[{detected_lang}] {text}"
        self.text_label.configure(text=formatted_text)
        
        # Force window update to compute actual geometry sizes
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        
        # Fetch screen size to prevent clipping off-screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Position offset: 15px right, 20px down from mouse
        pos_x = x + 15
        pos_y = y + 20
        
        # Boundary checks
        if pos_x + width > screen_width:
            pos_x = x - width - 10
        if pos_y + height > screen_height:
            pos_y = y - height - 10
            
        # Apply positioning
        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        self.root.deiconify()
        
        # Start fade-in animation
        self._fade_in()
        
    def _fade_in(self, target_alpha=0.96, step=0.24):
        """Animates window opacity from current to target_alpha."""
        if not self.root or not self.root.winfo_exists():
            return
            
        alpha = self.root.attributes("-alpha")
        if alpha < target_alpha:
            alpha = min(target_alpha, alpha + step)
            self.root.attributes("-alpha", alpha)
            self.fade_job = self.root.after(16, lambda: self._fade_in(target_alpha, step))
            
    def hide(self):
        """Hides the tooltip and resets alpha."""
        if self.fade_job:
            try:
                self.root.after_cancel(self.fade_job)
            except Exception:
                pass
            self.fade_job = None
            
        if self.root and self.root.winfo_exists():
            self.root.attributes("-alpha", 0.0)
            self.root.withdraw()
            
    def destroy(self):
        """Completely destroys the window."""
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None
