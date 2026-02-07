import os
import zipfile
import shutil
import glob
import hashlib
from pathlib import Path


def _sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def process_incoming_zips(source_folder: str, destination_folder: str) -> int:
    """
    Scans source_folder (e.g. OneDrive) for .zip files.
    Extracts any Audit report CSVs found inside to destination_folder.

    Improvements:
    - Extracts ANY *.csv that contains 'Audit_Report' (case-insensitive)
      to support slightly different naming versions.
    - Avoids duplicates more reliably using content hashes.
    - If the same filename already exists but the ZIP contains a newer/different file,
      it will save it using a de-duplicated name instead of silently skipping.
    - Ignores directory structure inside the zip (flattens to filename).
    """
    if not source_folder or not os.path.exists(source_folder):
        return 0

    os.makedirs(destination_folder, exist_ok=True)

    new_files_count = 0

    # Track existing files by hash to avoid duplicates even if filename differs
    existing_hashes = set()
    for existing in glob.glob(os.path.join(destination_folder, "*.csv")):
        try:
            existing_hashes.add(_sha256_file(existing))
        except Exception:
            continue

    zip_files = glob.glob(os.path.join(source_folder, "*.zip"))

    for zip_path in zip_files:
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                # Find audit CSVs (case-insensitive)
                members = z.namelist()
                csv_members = [
                    m for m in members
                    if m.lower().endswith(".csv") and "audit_report" in os.path.basename(m).lower()
                ]

                for member in csv_members:
                    filename = os.path.basename(member)
                    if not filename:
                        continue

                    base_target = os.path.join(destination_folder, filename)

                    # Extract to a temp file first so we can hash + decide what to do
                    tmp_target = base_target + ".tmp_extract"
                    try:
                        with z.open(member) as src, open(tmp_target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                    except Exception:
                        # Clean up tmp if partial
                        if os.path.exists(tmp_target):
                            os.remove(tmp_target)
                        continue

                    # Hash for de-dup
                    try:
                        file_hash = _sha256_file(tmp_target)
                    except Exception:
                        file_hash = None

                    if file_hash and file_hash in existing_hashes:
                        # Duplicate content -> discard
                        os.remove(tmp_target)
                        continue

                    # Decide final destination:
                    # - If base filename doesn't exist: move into place
                    # - If it exists but different content: keep both with suffix
                    if not os.path.exists(base_target):
                        os.replace(tmp_target, base_target)
                        new_files_count += 1
                        if file_hash:
                            existing_hashes.add(file_hash)
                        print(f"✅ Extracted: {filename}")
                        continue

                    # Filename exists; avoid overwrite by suffixing
                    stem = Path(filename).stem
                    suffix = Path(filename).suffix
                    i = 2
                    while True:
                        alt_name = f"{stem} ({i}){suffix}"
                        alt_target = os.path.join(destination_folder, alt_name)
                        if not os.path.exists(alt_target):
                            os.replace(tmp_target, alt_target)
                            new_files_count += 1
                            if file_hash:
                                existing_hashes.add(file_hash)
                            print(f"✅ Extracted (dedup name): {alt_name}")
                            break
                        i += 1

        except zipfile.BadZipFile:
            print(f"⚠️ Bad Zip: {zip_path}")
        except Exception as e:
            print(f"❌ Error on {zip_path}: {e}")

    return new_files_count
