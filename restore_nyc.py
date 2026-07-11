import json
import os
import re

transcript_path = r"C:\Users\barto\.gemini\antigravity-ide\brain\69677f83-fd17-4654-b804-6958c387e264\.system_generated\logs\transcript.jsonl"
nyc_dir = r"c:\Users\barto\Desktop\polymarket\weather\y_data\nyc"

os.makedirs(nyc_dir, exist_ok=True)

# Dictionary to hold the latest content for each file
recovered_files = {}

if os.path.exists(transcript_path):
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                step = json.loads(line)
                content = step.get('content', '')
                if not content:
                    continue
                
                # We look for diff blocks
                # Format: "The following changes were made by the USER to: c:\Users\barto\Desktop\polymarket\weather\y_data\nyc\styczen_2024.txt."
                
                parts = content.split("The following changes were made by the USER to: ")
                for part in parts[1:]:
                    filename_match = re.match(r"(.*\.txt)", part)
                    if not filename_match:
                        continue
                        
                    filepath = filename_match.group(1).strip()
                    if "nyc" not in filepath:
                        continue
                        
                    basename = os.path.basename(filepath)
                    
                    # Extract the diff block
                    diff_start = part.find("[diff_block_start]")
                    diff_end = part.find("[diff_block_end]")
                    
                    if diff_start != -1 and diff_end != -1:
                        diff_content = part[diff_start+18:diff_end]
                        lines = diff_content.split('\n')
                        
                        file_lines = []
                        for l in lines:
                            if l.startswith('+'):
                                file_lines.append(l[1:])
                            elif l.startswith(' ') or l == '':
                                pass
                                
                        if len(file_lines) > 2: # Check if it actually contains data
                            recovered_files[basename] = "\n".join(file_lines)
            except Exception as e:
                pass

    print(f"Znaleziono {len(recovered_files)} plików do odtworzenia.")
    for basename, text in recovered_files.items():
        out_path = os.path.join(nyc_dir, basename)
        with open(out_path, 'w', encoding='utf-8') as out_f:
            out_f.write(text)
        print(f"Odtworzono: {basename}")
else:
    print("Nie znaleziono pliku transcript.jsonl")
