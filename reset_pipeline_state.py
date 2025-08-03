#!/usr/bin/env python3
"""
Reset the pipeline state to allow fresh uploads and processing
"""

import os
import json
from datetime import datetime

def reset_pipeline_state():
    """Reset the pipeline state to start fresh."""
    
    print("🔄 RESETTING PIPELINE STATE")
    print("=" * 60)
    
    # Files that mark steps as "completed"
    files_to_remove = [
        './output/dfd_components.json',           # Step 2 - DFD Extraction
        './output/identified_threats.json',      # Step 3 - Threat Identification  
        './output/refined_threats.json',         # Step 4 - Threat Refinement
        './output/attack_paths.json',            # Step 5 - Attack Path Analysis
        './output/runtime_config.json',          # Saved configuration
    ]
    
    # Progress and state files
    state_files = [
        './output/step_2_progress.json',
        './output/step_3_progress.json', 
        './output/step_4_progress.json',
        './output/step_5_progress.json',
        './output/flask_call_intercept.json',
        './output/dfd_execution_debug.json',
    ]
    
    removed_count = 0
    
    print("🗑️  Removing pipeline state files:")
    
    for file_path in files_to_remove + state_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"   ✅ Removed: {os.path.basename(file_path)}")
                removed_count += 1
            except Exception as e:
                print(f"   ❌ Failed to remove {file_path}: {e}")
        else:
            print(f"   ⚪ Not found: {os.path.basename(file_path)}")
    
    # Optional: Clean up old uploaded files (keep only most recent)
    print(f"\n📁 Cleaning up old uploaded files:")
    
    dirs_to_clean = ['./uploads', './input_documents', './output']
    
    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            extracted_files = [f for f in os.listdir(dir_path) if f.endswith('_extracted.txt')]
            docx_files = [f for f in os.listdir(dir_path) if f.endswith('.docx')]
            
            all_upload_files = extracted_files + docx_files
            
            if len(all_upload_files) > 1:
                # Sort by modification time, keep only the most recent
                files_with_time = []
                for f in all_upload_files:
                    full_path = os.path.join(dir_path, f)
                    mtime = os.path.getmtime(full_path)
                    files_with_time.append((f, full_path, mtime))
                
                # Sort by time, newest first
                files_with_time.sort(key=lambda x: x[2], reverse=True)
                
                # Keep the newest, remove the rest
                for i, (filename, full_path, mtime) in enumerate(files_with_time):
                    if i == 0:
                        print(f"   ✅ Keeping newest: {filename}")
                    else:
                        try:
                            os.remove(full_path)
                            print(f"   🗑️  Removed old: {filename}")
                            removed_count += 1
                        except Exception as e:
                            print(f"   ❌ Failed to remove {filename}: {e}")
            elif len(all_upload_files) == 1:
                print(f"   ✅ Keeping single file: {all_upload_files[0]}")
            else:
                print(f"   ⚪ No upload files in {dir_path}")
    
    print(f"\n📊 Summary:")
    print(f"   🗑️  Files removed: {removed_count}")
    print(f"   ⏰ Reset completed: {datetime.now()}")
    print(f"\n✅ Pipeline state reset complete!")
    print(f"   🔄 Restart Flask app to apply changes")
    print(f"   📤 You can now upload new documents")
    
    return removed_count

if __name__ == "__main__":
    reset_pipeline_state()
