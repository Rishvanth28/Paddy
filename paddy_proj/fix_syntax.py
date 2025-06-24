"""
This script fixes syntax errors in the reports.py file that occurred during the previous update.
"""
import os
import re

# Path to the reports.py file
REPORTS_FILE = os.path.join('c:\\', 'projects', 'Paddy', 'paddy_proj', 'paddy_app', 'reports.py')

def fix_syntax_errors():
    """Fix syntax errors in reports.py"""
    with open(REPORTS_FILE, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Fix any remaining syntax issues with proper indentation
    # Check all for loops and fix indentation issues
    for_loop_pattern = re.compile(r'for\s+\w+\s+in\s+[^:]+:(?:\s+)(\S+)', re.MULTILINE)
    content = for_loop_pattern.sub(r'for \1 in \2:\n            \3', content)
    
    # Fix specific issue with column headers
    problem_line = "for header in ordered_columns:            if header == 'id':"
    fixed_line = "for header in ordered_columns:\n            if header == 'id':"
    content = content.replace(problem_line, fixed_line)
    
    # Ensure proper spacing around operators and parentheses
    content = re.sub(r'(\w+)\((\w+)', r'\1(\2', content)
    
    # Write the fixed content back to the file
    with open(REPORTS_FILE, 'w', encoding='utf-8') as file:
        file.write(content)
    
    return "Successfully fixed syntax errors in reports.py"

if __name__ == "__main__":
    result = fix_syntax_errors()
    print(result)
