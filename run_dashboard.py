import os
import sys
import streamlit.web.cli as stcli

def resolve_path(path):
    # If we are running in the PyInstaller bundle
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, path)
    # If we are running normally
    return os.path.join(os.getcwd(), path)

if __name__ == "__main__":
    # 1. Ensure the PyInstaller temp folder is in the system path
    # This allows app.py to import header, main_section, etc.
    if hasattr(sys, "_MEIPASS"):
        sys.path.append(sys._MEIPASS)

    # 2. Point Streamlit to the internal app.py
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("app.py"),
        "--global.developmentMode=false",
    ]
    
    # 3. Launch
    sys.exit(stcli.main())