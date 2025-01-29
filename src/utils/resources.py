import os
import sys

def get_icon_path():
    try:
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_path = sys._MEIPASS
        else:
            # Running as script
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        icon_path = os.path.join(base_path, 'assets', 'app_icon.ico')
        return icon_path if os.path.exists(icon_path) else None
        
    except Exception as e:
        print(f"Error getting icon path: {e}")
        return None 