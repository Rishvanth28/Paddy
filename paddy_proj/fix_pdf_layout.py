"""
This script updates the reports.py file to improve PDF layout and alignment
by fixing column title collisions and making the headers responsive.
"""
import os
import re

# Path to the reports.py file
REPORTS_FILE = os.path.join('c:\\', 'projects', 'Paddy', 'paddy_proj', 'paddy_app', 'reports.py')

def fix_pdf_column_alignment():
    """Fix the PDF column alignment in reports.py"""
    with open(REPORTS_FILE, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 1. Replace all column headers with multi-line versions
    # Replace single-line headers with multi-line headers
    replacements = [
        ("readable_headers.append('Order ID')", "readable_headers.append('Order\\nID')"),
        ("readable_headers.append('Customer')", "readable_headers.append('Customer\\nName')"),
        ("readable_headers.append('Order Date')", "readable_headers.append('Order\\nDate')"),
        ("readable_headers.append('Product Type')", "readable_headers.append('Product\\nType')"),
        ("readable_headers.append('Quantity')", "readable_headers.append('Qty')"),
        ("readable_headers.append('Total Amount')", "readable_headers.append('Total\\nAmount')"),
        ("readable_headers.append('Pending Amount')", "readable_headers.append('Pending\\nAmount')"),
        ("readable_headers.append('Delivery Status')", "readable_headers.append('Delivery\\nStatus')"),
        ("readable_headers.append('Payment Status')", "readable_headers.append('Payment\\nStatus')"),
        ("readable_headers.append('Product Name')", "readable_headers.append('Product\\nName')"),
        ("readable_headers.append('Batch Number')", "readable_headers.append('Batch\\nNumber')"),
        ("readable_headers.append('Expiry Date')", "readable_headers.append('Expiry\\nDate')"),
        ("readable_headers.append('Price per Unit')", "readable_headers.append('Price\\nper Unit')"),
        ("readable_headers.append('Item Total')", "readable_headers.append('Item\\nTotal')"),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    # 2. Increase column widths for better spacing
    # Update rice/paddy table column widths
    rice_paddy_widths_superadmin = """            col_widths = [
                70,   # Order ID - increased width for multiline header
                80,   # Admin name
                80,   # Customer name
                70,   # Order date
                70,   # Product type
                50,   # Quantity
                70,   # Total amount
                70,   # Pending amount
                70,   # Delivery status
                70    # Payment status
            ]"""
    
    rice_paddy_widths_admin = """            col_widths = [
                70,   # Order ID - increased width for multiline header
                95,   # Customer name
                70,   # Order date
                70,   # Product type
                50,   # Quantity
                70,   # Total amount
                70,   # Pending amount
                70,   # Delivery status
                70    # Payment status
            ]"""
    
    # Find and replace the existing column width definitions
    superadmin_pattern = re.compile(r'if is_superadmin:\s+col_widths = \[\s+\d+,\s+# Order ID.*?\]', re.DOTALL)
    admin_pattern = re.compile(r'else:\s+col_widths = \[\s+\d+,\s+# Order ID.*?\]', re.DOTALL)
    
    # Find the matches
    superadmin_match = superadmin_pattern.search(content)
    admin_match = admin_pattern.search(content)
    
    # Replace if found
    if superadmin_match:
        content = content.replace(superadmin_match.group(0), f"if is_superadmin:\n{rice_paddy_widths_superadmin}")
    
    if admin_match:
        content = content.replace(admin_match.group(0), f"else:\n{rice_paddy_widths_admin}")
    
    # 3. Update pesticide table column widths
    pesticide_widths_superadmin = """            col_widths = [
                60,   # Order ID - increased for multiline header
                55,   # Admin name
                55,   # Customer name
                55,   # Order date
                65,   # Product name
                55,   # Batch number
                55,   # Expiry date
                40,   # Quantity
                35,   # Unit
                55,   # Price per unit
                55,   # Item total
                55,   # Delivery status
                55    # Payment status
            ]"""
    
    pesticide_widths_admin = """            col_widths = [
                60,   # Order ID - increased for multiline header
                60,   # Customer name
                55,   # Order date
                65,   # Product name
                55,   # Batch number
                55,   # Expiry date
                40,   # Quantity
                35,   # Unit
                55,   # Price per unit
                55,   # Item total
                55,   # Delivery status
                55    # Payment status
            ]"""
    
    # Find the pesticide column width sections
    pesticide_section = "# Define column widths - carefully adjusted for pesticide orders"
    if pesticide_section in content:
        # Find the section start
        section_start = content.find(pesticide_section)
        
        # Find the if-else block after this section
        if_start = content.find("if is_superadmin:", section_start)
        if if_start != -1:
            # Find the end of the superadmin block
            block_end = content.find("]", if_start)
            if block_end != -1:
                # Extract the superadmin block
                superadmin_block = content[if_start:block_end+1]
                
                # Find the else block
                else_start = content.find("else:", block_end)
                if else_start != -1:
                    else_block_end = content.find("]", else_start)
                    if else_block_end != -1:
                        # Extract the else block
                        else_block = content[else_start:else_block_end+1]
                        
                        # Replace both blocks
                        content = content.replace(superadmin_block, f"if is_superadmin:\n{pesticide_widths_superadmin}")
                        content = content.replace(else_block, f"else:\n{pesticide_widths_admin}")
    
    # 4. Update table styling for both tables to enhance header appearance
    header_styling = """            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),  # Smaller font size for headers
            ('BOTTOMPADDING', (0, 0), (-1, 0), 14),  # Increased padding for multi-line headers
            ('TOPPADDING', (0, 0), (-1, 0), 14),     # Increased padding for multi-line headers
            ('LEFTPADDING', (0, 0), (-1, 0), 6),     # Increased left padding
            ('RIGHTPADDING', (0, 0), (-1, 0), 6),    # Increased right padding
            
            # Special border for column headers to visually separate them
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.white),
            ('LINEAFTER', (0, -1), (-2, 0), 0.5, colors.white),"""
    
    # Find and replace header styling in both tables
    old_header_styling_pattern = re.compile(r'# Header row styling.*?# Data rows styling', re.DOTALL)
    matches = old_header_styling_pattern.finditer(content)
    
    # Replace each match
    for match in list(matches):
        old_styling = match.group(0)
        new_styling = header_styling + "\n            \n            # Data rows styling"
        content = content.replace(old_styling, new_styling)
    
    # 5. Increase the document margins for better layout
    doc_creation = """    # Create the PDF object in landscape orientation with larger margins for better readability
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),  # Using landscape orientation
        rightMargin=60,          # Increased right margin
        leftMargin=60,           # Increased left margin
        topMargin=60,            # Increased top margin
        bottomMargin=60,         # Increased bottom margin
        allowSplitting=1,        # Control page breaks
        title=filename,          # Add metadata
        author="Paddy Management System"
    )"""
    
    # Find and replace the document creation
    old_doc_pattern = re.compile(r'# Create the PDF object in landscape orientation.*?author="Paddy Management System"\s+\)', re.DOTALL)
    old_doc_match = old_doc_pattern.search(content)
    
    if old_doc_match:
        content = content.replace(old_doc_match.group(0), doc_creation)
    
    # Write the updated content back to the file
    with open(REPORTS_FILE, 'w', encoding='utf-8') as file:
        file.write(content)
    
    return "Successfully updated PDF column alignment in reports.py"

if __name__ == "__main__":
    result = fix_pdf_column_alignment()
    print(result)
