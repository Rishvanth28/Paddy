import os
import re
import glob

# Find all HTML template files
template_directory = 'paddy_app/templates'
template_files = glob.glob(f'{template_directory}/**/*.html', recursive=True)

# Patterns to replace
patterns = [
    (r'class="i18n"\s+data-i18n="[^"]*"', ''), # Remove class and data attribute
    (r'data-i18n="[^"]*"', ''),  # Remove just the data attribute
]

for file_path in template_files:
    print(f"Processing {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Apply replacements
    modified_content = content
    for pattern, replacement in patterns:
        modified_content = re.sub(pattern, replacement, modified_content)
    
    # Only write if changes were made
    if modified_content != content:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(modified_content)
        print(f"Updated {file_path}")
    else:
        print(f"No changes needed in {file_path}")

print("Done processing all template files")
