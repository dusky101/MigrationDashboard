"""
Status Tracker

Manages migration workflow status for each user/device.
Stores data in CSV format for simplicity and backward compatibility.
"""

import os
import pandas as pd
from typing import Tuple

# Constants
STATUS_FILE = "status_tracker.csv"

STATUS_OPTIONS = [
    "Not Started",
    "Machine Audit Run",
    "Migration setup completed",
    "Migration Run",
    "Complete",
]


def load_status() -> pd.DataFrame:
    """
    Loads the status tracker CSV.

    Enhancements:
    - Normalises index values (lowercase + strip) to reduce mismatch issues.
    - Handles backward compatibility if columns are missing.
    - Always returns a DF indexed by "User".
    
    Returns:
        DataFrame indexed by User with columns: Status, Notes, EntraCreated
    """
    if os.path.exists(STATUS_FILE):
        df = pd.read_csv(STATUS_FILE)

        if "User" not in df.columns and len(df.columns) > 0:
            df = df.rename(columns={df.columns[0]: "User"})

        if "User" in df.columns:
            df["User"] = df["User"].astype(str).str.strip().str.lower()
            df = df.set_index("User")
        else:
            return pd.DataFrame(columns=["Status", "Notes", "EntraCreated"]).set_index(
                pd.Index([], name="User")
            )

        if "Status" not in df.columns:
            df["Status"] = "Not Started"
        if "Notes" not in df.columns:
            df["Notes"] = ""
        if "EntraCreated" not in df.columns:
            df["EntraCreated"] = False

        df["Status"] = df["Status"].fillna("Not Started").astype(str)
        df["Notes"] = df["Notes"].fillna("").astype(str)
        df["EntraCreated"] = df["EntraCreated"].fillna(False).astype(bool)

        return df

    return pd.DataFrame(columns=["Status", "Notes", "EntraCreated"]).set_index(
        pd.Index([], name="User")
    )


def save_status(user_key: str, status: str, notes: str, entra_created: bool) -> None:
    """
    Saves Status, Notes, and EntraCreated flag to CSV.
    
    Args:
        user_key: User identifier
        status: Migration status
        notes: Engineer notes
        entra_created: Whether user is created in MS Entra
    """
    user_key = str(user_key).strip().lower()
    df = load_status()

    df.loc[user_key, "Status"] = status
    df.loc[user_key, "Notes"] = notes
    df.loc[user_key, "EntraCreated"] = bool(entra_created)

    df.to_csv(STATUS_FILE, index_label="User")


def get_status_for_user(user_key: str) -> Tuple[str, str, bool]:
    """
    Get status information for a specific user.
    
    Args:
        user_key: User identifier
        
    Returns:
        Tuple of (status, notes, entra_created)
    """
    user_key = str(user_key).strip().lower()
    df = load_status()
    
    if user_key in df.index:
        return (
            df.loc[user_key, "Status"],
            df.loc[user_key, "Notes"],
            df.loc[user_key, "EntraCreated"]
        )
    
    return ("Not Started", "", False)