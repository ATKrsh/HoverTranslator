import time
import ctypes
import re

# Initialize Windows UI Automation
# We will import uiautomation inside functions or lazily to ensure it loads correctly
auto = None

def load_uiautomation():
    global auto
    if auto is None:
        import uiautomation as uiaut
        auto = uiaut
        # Set some search properties for safety
        auto.SetGlobalSearchTimeout(1.0)
    return auto

# Windows API structures for Cursor Position
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_mouse_position():
    """Gets the current screen coordinates of the mouse cursor."""
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def get_active_window_title():
    """Retrieves the title of the currently active/focused window."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value.strip()
    except Exception:
        return ""

# Control types to ignore when extracting Name property
# These are structural and their names are usually titles/descriptions of containers rather than text content.
IGNORED_CONTROL_TYPES = {
    "WindowControl",
    "TitleBarControl",
    "MenuBarControl",
    "ScrollBarControl",
    "ThumbControl",
    "PaneControl",  # Panes can contain text but their own Name is often just structural (like "Workspace")
    "SplitButtonControl",
    "HeaderControl",
    "HeaderItemControl"
}

def extract_text_from_control(control, x, y):
    """
    Attempts to extract text under the given coordinates from a UI automation control.
    Uses a tiered approach:
    1. TextPattern (document/text range)
    2. ValuePattern (inputs/textboxes)
    3. Name / HelpText (labels/buttons/list items)
    """
    if not control:
        return None

    # Tier 1: Check for TextPattern (rich text areas, web browsers, documents)
    try:
        if control.HasPattern(10024):  # 10024 is the pattern ID for TextPattern
            text_pattern = control.GetTextPattern()
            if text_pattern:
                # Get text range under the cursor
                text_range = text_pattern.RangeFromPoint((x, y))
                if text_range:
                    # Expand to a Line or Paragraph to get context rather than a single word
                    # TextUnit.Line = 3, TextUnit.Paragraph = 4
                    try:
                        text_range.ExpandToEnclosingUnit(3) # Expand to line
                    except Exception:
                        pass
                    
                    text = text_range.GetText()
                    if text and text.strip():
                        return text.strip()
    except Exception:
        pass

    # Tier 2: Check ValuePattern (forms, input boxes)
    try:
        if control.HasPattern(10002):  # 10002 is ValuePattern
            val_pattern = control.GetValuePattern()
            if val_pattern:
                val = val_pattern.Value
                if val and val.strip():
                    return val.strip()
    except Exception:
        pass

    # Tier 3: General Name / HelpText (labels, list items, buttons)
    # Check control type first to prevent extracting window/container titles as text
    try:
        control_type = control.ControlTypeName
        if control_type not in IGNORED_CONTROL_TYPES:
            name = control.Name
            # Make sure it isn't the active window's title (e.g. if we hovered over background)
            if name and name.strip():
                name_clean = name.strip()
                active_title = get_active_window_title()
                if name_clean != active_title and len(name_clean) > 1:
                    return name_clean
    except Exception:
        pass

    return None

def get_text_under_cursor_at(x, y):
    """Gets the text currently hovered under the specific mouse coordinates (x, y)."""
    try:
        uiaut = load_uiautomation()
        control = uiaut.ControlFromPoint(x, y)
        if control:
            text = extract_text_from_control(control, x, y)
            if text:
                text_clean = text.strip()
                # Truncate text if it's very large to prevent UI lag and API limits
                if len(text_clean) > 400:
                    text_clean = text_clean[:400] + "..."
                return text_clean
    except Exception:
        pass
    return None

def get_text_under_cursor():
    """Gets the text currently hovered under the mouse cursor."""
    try:
        x, y = get_mouse_position()
        return get_text_under_cursor_at(x, y)
    except Exception:
        pass
    return None

def clean_text(text):
    """Cleans up text, stripping extra whitespaces, newlines, and filtering out numbers/symbols."""
    if not text:
        return ""
    # Normalize whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    # Filter out text that is purely numeric or punctuation
    # We require the text to have at least one alphabetic letter and be at least 2 characters long
    has_letters = any(c.isalpha() for c in text)
    if not has_letters or len(text) < 2:
        return ""
    return text

LANGUAGE_MAP = {
    'af': 'Afrikaans', 'sq': 'Albanian', 'am': 'Amharic', 'ar': 'Arabic', 'hy': 'Armenian', 'az': 'Azerbaijani',
    'eu': 'Basque', 'be': 'Belarusian', 'bn': 'Bengali', 'bs': 'Bosnian', 'bg': 'Bulgarian', 'ca': 'Catalan',
    'ceb': 'Cebuano', 'ny': 'Chichewa', 'zh-CN': 'Chinese', 'zh-TW': 'Chinese', 'zh': 'Chinese', 'co': 'Corsican',
    'hr': 'Croatian', 'cs': 'Czech', 'da': 'Danish', 'nl': 'Dutch', 'en': 'English', 'eo': 'Esperanto',
    'et': 'Estonian', 'tl': 'Filipino', 'fi': 'Finnish', 'fr': 'French', 'fy': 'Frisian', 'gl': 'Galician',
    'ka': 'Georgian', 'de': 'German', 'el': 'Greek', 'gu': 'Gujarati', 'ht': 'Haitian Creole', 'ha': 'Hausa',
    'haw': 'Hawaiian', 'iw': 'Hebrew', 'he': 'Hebrew', 'hi': 'Hindi', 'hmn': 'Hmong', 'hu': 'Hungarian',
    'is': 'Icelandic', 'ig': 'Igbo', 'id': 'Indonesian', 'ga': 'Irish', 'it': 'Italian', 'ja': 'Japanese',
    'jw': 'Javanese', 'kn': 'Kannada', 'kk': 'Kazakh', 'km': 'Khmer', 'rw': 'Kinyarwanda', 'ko': 'Korean',
    'ku': 'Kurdish', 'ky': 'Kyrgyz', 'lo': 'Lao', 'la': 'Latin', 'lv': 'Latvian', 'lt': 'Lithuanian',
    'lb': 'Luxembourgish', 'mk': 'Macedonian', 'mg': 'Malagasy', 'ms': 'Malay', 'ml': 'Malayalam',
    'mt': 'Maltese', 'mi': 'Maori', 'mr': 'Marathi', 'mn': 'Mongolian', 'my': 'Myanmar', 'ne': 'Nepali',
    'no': 'Norwegian', 'or': 'Oriya', 'ps': 'Pashto', 'fa': 'Persian', 'pl': 'Polish', 'pt': 'Portuguese',
    'pa': 'Punjabi', 'ro': 'Romanian', 'ru': 'Russian', 'sm': 'Samoan', 'gd': 'Scots Gaelic', 'sr': 'Serbian',
    'st': 'Sesotho', 'sn': 'Shona', 'sd': 'Sindhi', 'si': 'Sinhala', 'sk': 'Slovak', 'sl': 'Slovenian',
    'so': 'Somali', 'es': 'Spanish', 'su': 'Sundanese', 'sw': 'Swahili', 'sv': 'Swedish', 'tg': 'Tajik',
    'ta': 'Tamil', 'tt': 'Tatar', 'te': 'Telugu', 'th': 'Thai', 'tr': 'Turkish', 'tk': 'Turkmen',
    'uk': 'Ukrainian', 'ur': 'Urdu', 'ug': 'Uyghur', 'uz': 'Uzbek', 'vi': 'Vietnamese', 'cy': 'Welsh',
    'xh': 'Xhosa', 'yi': 'Yiddish', 'yo': 'Yoruba', 'zu': 'Zulu'
}

def check_cjk_language(text):
    """Detects if text contains Chinese, Japanese, or Korean characters and returns the language name."""
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
    has_japanese = any('\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff' for char in text)
    has_korean = any('\uac00' <= char <= '\ud7af' for char in text)
    
    if has_korean:
        return "Korean"
    elif has_japanese:
        return "Japanese"
    elif has_chinese:
        return "Chinese"
    return None

class HoverTranslator:
    def __init__(self):
        pass
        
    def translate(self, text, target_lang="en"):
        """
        Translates text to target_lang ('en' or 'hi').
        Returns (translated_text, source_language_name) or (None, None) if translation is not needed or fails.
        """
        cleaned = clean_text(text)
        if not cleaned:
            return None, None
            
        import urllib.request
        import urllib.parse
        import json
        
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": target_lang,
                "dt": "t",
                "q": cleaned
            }
            query_string = urllib.parse.urlencode(params)
            full_url = f"{url}?{query_string}"
            
            req = urllib.request.Request(
                full_url, 
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            
            with urllib.request.urlopen(req, timeout=2.0) as response:
                content = response.read().decode("utf-8")
                data = json.loads(content)
                
            if not data or not data[0]:
                return None, None
                
            segments = []
            for segment in data[0]:
                if segment and segment[0]:
                    segments.append(segment[0])
            translated = "".join(segments)
            
            translated_clean = clean_text(translated)
            if not translated_clean:
                return None, None
                
            # If translation matches original (ignoring case), skip showing tooltip
            if cleaned.lower() == translated_clean.lower():
                return None, None
                
            source_code = data[2] if len(data) > 2 else "auto"
            
            # Map code to friendly language name
            source_lang = LANGUAGE_MAP.get(source_code, source_code.upper())
            
            # CJK Override Check: Ensure Chinese, Japanese, or Korean characters are detected accurately
            cjk_lang = check_cjk_language(cleaned)
            if cjk_lang:
                source_lang = cjk_lang
                
            return translated_clean, source_lang
            
        except Exception as e:
            print(f"Translation Error: {e}")
            return None, None

