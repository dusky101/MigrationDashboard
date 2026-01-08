import os
import zipfile
import shutil
import glob

def process_incoming_zips(source_folder, destination_folder):
    """
    Scans source_folder (OneDrive) for .zip files.
    Extracts any 'Audit_Report_*.csv' found inside them to destination_folder.
    """
    if not os.path.exists(source_folder):
        return 0
    
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    new_files_count = 0
    
    # Get all zip files in the source folder
    zip_files = glob.glob(os.path.join(source_folder, "*.zip"))
    
    for zip_path in zip_files:
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Find the specific Audit CSV inside the Zip (ignoring other files like drivers)
                csv_files = [f for f in z.namelist() if "Audit_Report" in f and f.endswith(".csv")]
                
                for csv_file in csv_files:
                    # We flatten the path: ignore folders inside the zip, just take the filename
                    filename = os.path.basename(csv_file)
                    target_path = os.path.join(destination_folder, filename)
                    
                    # Only extract if we haven't already (Basic caching)
                    # You could improve this by checking file modification times if needed
                    if not os.path.exists(target_path):
                        with z.open(csv_file) as source, open(target_path, "wb") as target:
                            shutil.copyfileobj(source, target)
                        new_files_count += 1
                        print(f"✅ Extracted: {filename}")
                        
        except zipfile.BadZipFile:
            print(f"⚠️ Bad Zip: {zip_path}")
        except Exception as e:
            print(f"❌ Error on {zip_path}: {e}")

    return new_files_count