import pandas as pd
import os

def find_audit_file(folder_path, user_email):
    """Looks for an audit file matching the user in the specified folder."""
    if not os.path.exists(folder_path):
        return None

    try:
        files = os.listdir(folder_path)
    except:
        return None
    
    if not user_email or not isinstance(user_email, str):
        return None
        
    # Logic: 'marc.oliff@buddy.hr' -> search for 'marc' and 'oliff' in filename
    parts = user_email.split('@')[0].replace('.', ' ').split(' ')
    parts = [p.lower() for p in parts if len(p) > 2]
    
    if not parts: return None

    for file in files:
        if file.endswith(".csv"):
            filename_lower = file.lower()
            if all(part in filename_lower for part in parts):
                return os.path.join(folder_path, file)
    return None

def parse_audit_csv(file_path):
    """
    Reads the Migration Auditor CSV.
    INCLUDES RETROACTIVE FIX: intelligently handles 'bad' rows from 
    older app versions where commas in specs (e.g. 'Mac14,6') broke the CSV structure.
    """
    try:
        # 1. Read raw lines instead of using pd.read_csv directly
        # 'errors=replace' prevents crashes on weird characters
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        # 2. Find where the real header starts
        start_row = -1
        for i, line in enumerate(lines):
            # Check for the header row (allowing for potential leading/trailing whitespace)
            if "TYPE" in line and "DEVELOPER" in line and "NAME" in line:
                start_row = i
                break
        
        if start_row == -1: 
            return None
        
        # 3. Manual Parsing Logic
        data = []
        headers = ['TYPE', 'DEVELOPER', 'NAME', 'DETAILS']
        
        # Iterate through lines AFTER the header
        for line in lines[start_row + 1:]:
            line = line.strip()
            if not line: continue 
            
            # Split by comma
            parts = line.split(',')
            
            # If we have less than 4 parts, the row is broken/empty -> skip
            if len(parts) < 4:
                continue
                
            # If we have exactly 4 parts, it's a perfect row
            if len(parts) == 4:
                data.append([p.strip() for p in parts])
            
            # If we have MORE than 4 parts, it means a field contained a comma (The Bug)
            # The structure is always: TYPE, DEVELOPER, NAME, DETAILS
            # So the first 3 are static, and everything else belongs to DETAILS.
            else:
                row_type = parts[0].strip()
                developer = parts[1].strip()
                name = parts[2].strip()
                
                # Join all remaining parts back together to fix the split
                # e.g., ["Mac14", "6"] -> "Mac14,6"
                details = ",".join(parts[3:]).strip()
                
                data.append([row_type, developer, name, details])
            
        # 4. Create DataFrame from our clean list
        if not data:
            return pd.DataFrame(columns=headers)
            
        return pd.DataFrame(data, columns=headers)
        
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None