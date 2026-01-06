import os
import sys
import streamlit.web.cli as stcli

def resolve_path(path):
    # This function helps the app find files (like app.py) 
    # whether it's running normally or inside the "Frozen" app.
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.getcwd(), path)

if __name__ == "__main__":
    # This simulates running "streamlit run app.py" from the command line
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("app.py"),
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())