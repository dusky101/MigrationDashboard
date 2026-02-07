import os
import re
import csv
import pandas as pd


def find_audit_file(folder_path: str, user_key: str):
    """
    Looks for an audit file matching the user in the specified folder.

    Updated behaviour:
    - Works with either an email (e.g. marc.oliff@company.com) OR an audit-only key
      (e.g. "marc oliff" derived from filenames).
    - Uses multiple matching strategies, in priority order:
        1) Direct substring match of the full user_key in the filename
        2) Email local-part token match (first/last) if user_key looks like an email
        3) Token match for name-like keys (splitting on spaces/dots/underscores)
    """
    if not folder_path or not os.path.exists(folder_path):
        return None

    try:
        files = os.listdir(folder_path)
    except Exception:
        return None

    if not user_key or not isinstance(user_key, str):
        return None

    user_key_norm = user_key.strip().lower()

    # Candidate csv files only
    csv_files = [f for f in files if f.lower().endswith(".csv")]
    if not csv_files:
        return None

    # 1) Direct match (best for audit-only keys derived from filename)
    for f in csv_files:
        if user_key_norm and user_key_norm in f.lower():
            return os.path.join(folder_path, f)

    # Helper: tokenise filenames
    def filename_tokens(name: str):
        stem = os.path.splitext(os.path.basename(name))[0].lower()
        stem = stem.replace("-", " ").replace("_", " ").replace(".", " ")
        stem = re.sub(r"\s+", " ", stem).strip()
        toks = [t for t in stem.split(" ") if len(t) > 1]
        return set(toks)

    # 2) If it looks like an email, token-match the local-part
    if "@" in user_key_norm:
        local = user_key_norm.split("@", 1)[0]
        local = local.replace(".", " ")
        parts = [p for p in local.split(" ") if len(p) > 2]
        parts = [p.lower() for p in parts]

        if parts:
            for f in csv_files:
                ftoks = filename_tokens(f)
                if all(p in ftoks for p in parts):
                    return os.path.join(folder_path, f)

    # 3) Name-like token match
    name_key = re.sub(r"(?i)^audit[\s_\-]*report[\s_\-]*", "", user_key_norm)
    name_key = name_key.replace(".", " ").replace("-", " ").replace("_", " ")
    name_key = re.sub(r"\s+", " ", name_key).strip()
    parts = [p for p in name_key.split(" ") if len(p) > 2]

    if parts:
        for f in csv_files:
            ftoks = filename_tokens(f)
            if all(p in ftoks for p in parts):
                return os.path.join(folder_path, f)

    return None


def parse_audit_csv(file_path: str) -> pd.DataFrame | None:
    """
    Reads the Migration Auditor CSV.

    This parser is intentionally resilient because audit outputs can vary over time.

    What it supports:
    - Current CSV shape (TYPE, DEVELOPER, NAME, DETAILS)
    - Future extra columns (if your auditor adds more fields later)
    - Older "comma bug" rows where an unquoted comma inside a value caused extra splits
      (e.g., Mac14,6)
    - Proper CSV quoting via python's csv module (handles quoted commas correctly)

    Strategy:
    1) Read raw lines and locate the header row.
    2) Parse subsequent rows with csv.reader (so quotes are honoured).
    3) If a row has more fields than headers, merge the overflow into the LAST column.
       (This preserves any new extra columns you may add later.)
    """
    if not file_path or not os.path.exists(file_path):
        return None

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as f:
            lines = f.readlines()

        # Locate header row (allowing for future extra columns)
        start_row = -1
        header_fields = None

        for i, line in enumerate(lines):
            # Strip BOM and whitespace for detection
            test = line.strip().lstrip("\ufeff")
            if not test:
                continue

            # We expect TYPE/NAME/DETAILS at minimum; DEVELOPER is usually present
            if "TYPE" in test and "NAME" in test and "DETAILS" in test:
                # Parse the header line properly using csv.reader
                header_fields = next(csv.reader([test], delimiter=",", quotechar='"'))
                header_fields = [h.strip().lstrip("\ufeff") for h in header_fields if h.strip()]
                if header_fields and "TYPE" in header_fields and "NAME" in header_fields and "DETAILS" in header_fields:
                    start_row = i
                    break

        if start_row == -1 or not header_fields:
            return None

        headers = header_fields

        # Parse data rows
        data_rows = []
        reader = csv.reader(
            (ln.strip() for ln in lines[start_row + 1:] if ln.strip()),
            delimiter=",",
            quotechar='"',
            skipinitialspace=True,
        )

        for parts in reader:
            if not parts:
                continue

            # Normalise field count vs headers
            if len(parts) < len(headers):
                # Skip broken/short lines rather than guessing
                continue

            if len(parts) == len(headers):
                data_rows.append([p.strip() for p in parts])
                continue

            # More fields than headers -> merge overflow into last column
            fixed = [p.strip() for p in parts[: len(headers) - 1]]
            overflow = ",".join(p.strip() for p in parts[len(headers) - 1 :])
            fixed.append(overflow)
            data_rows.append(fixed)

        if not data_rows:
            return pd.DataFrame(columns=headers)

        df = pd.DataFrame(data_rows, columns=headers)

        # Defensive cleanup for expected columns
        for col in ["TYPE", "DEVELOPER", "NAME", "DETAILS"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        return df

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None
