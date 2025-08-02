#!/usr/bin/env python3
"""
Analyze the structure of info_to_dfds.py to understand why it's not producing output
"""

import os
import re

def analyze_script_structure():
    print("🔍 ANALYZING info_to_dfds.py STRUCTURE")
    print("=" * 60)
    
    script_path = './info_to_dfds.py'
    
    if not os.path.exists(script_path):
        print(f"❌ Script not found: {script_path}")
        return
    
    with open(script_path, 'r') as f:
        content = f.read()
    
    print(f"📄 File size: {len(content)} characters")
    print(f"📄 Lines: {len(content.splitlines())}")
    print()
    
    # Look for key patterns
    patterns = {
        'imports': r'^(import|from)\s+.*$',
        'class_definitions': r'^class\s+(\w+).*:',
        'function_definitions': r'^def\s+(\w+)\s*\(',
        'async_functions': r'^async\s+def\s+(\w+)\s*\(',
        'main_execution': r'if\s+__name__\s*==\s*["\']__main__["\']',
        'logging_calls': r'logger\.',
        'file_operations': r'(open\(|with open)',
        'json_operations': r'json\.(dump|load)',
        'environment_vars': r'os\.getenv|os\.environ'
    }
    
    for pattern_name, pattern in patterns.items():
        matches = re.findall(pattern, content, re.MULTILINE)
        print(f"{pattern_name.replace('_', ' ').title()}: {len(matches)}")
        if matches and len(matches) < 10:  # Show details for smaller lists
            for match in matches[:5]:
                print(f"   - {match}")
            if len(matches) > 5:
                print(f"   ... and {len(matches) - 5} more")
        print()
    
    # Look for main execution block
    main_match = re.search(r'if\s+__name__\s*==\s*["\']__main__["\']:.*?(?=\n\S|\Z)', content, re.DOTALL)
    if main_match:
        print("🎯 MAIN EXECUTION BLOCK:")
        print("-" * 30)
        main_block = main_match.group(0)
        lines = main_block.split('\n')
        for i, line in enumerate(lines[:20]):  # First 20 lines
            print(f"{i+1:2d}: {line}")
        if len(lines) > 20:
            print(f"    ... and {len(lines) - 20} more lines")
    else:
        print("❌ No main execution block found!")
    
    print()
    
    # Look for output file creation
    output_patterns = [
        r'dfd_components\.json',
        r'DFD_OUTPUT_PATH',
        r'json\.dump',
        r'\.write\(',
        r'save.*file'
    ]
    
    print("🔍 OUTPUT FILE CREATION PATTERNS:")
    print("-" * 30)
    for pattern in output_patterns:
        matches = re.findall(f'.*{pattern}.*', content, re.IGNORECASE)
        if matches:
            print(f"{pattern}:")
            for match in matches[:3]:
                print(f"   {match.strip()}")
        else:
            print(f"{pattern}: No matches")
    
    print()
    
    # Look for error handling
    error_patterns = [
        r'try:',
        r'except.*:',
        r'raise',
        r'return.*error',
        r'sys\.exit'
    ]
    
    print("🚨 ERROR HANDLING:")
    print("-" * 30)
    for pattern in error_patterns:
        count = len(re.findall(pattern, content, re.IGNORECASE))
        print(f"{pattern}: {count} occurrences")

def run_simple_execution_test():
    """Try to run the script with Python's exec to see what happens"""
    print("\n" + "=" * 60)
    print("🧪 SIMPLE EXECUTION TEST")
    print("=" * 60)
    
    try:
        # Set up environment
        os.environ.update({
            'INPUT_DIR': './input_documents',
            'OUTPUT_DIR': './output',
            'DFD_OUTPUT_PATH': './output/dfd_components.json',
            'LOG_LEVEL': 'DEBUG'
        })
        
        print("Running exec() on info_to_dfds.py...")
        
        with open('./info_to_dfds.py', 'r') as f:
            script_content = f.read()
        
        # Execute the script content
        exec(script_content)
        
        print("✅ Script executed without Python errors")
        
        # Check if output was created
        if os.path.exists('./output/dfd_components.json'):
            print("✅ Output file was created!")
        else:
            print("❌ No output file created")
            
    except Exception as e:
        print(f"❌ Execution error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_script_structure()
    run_simple_execution_test()