def number_to_words_indian(num):
    """Convert a number to words using the Indian numbering system (lakhs, crores)"""
    
    # Define word representations
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 
            'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 
            'Seventeen', 'Eighteen', 'Nineteen']
    
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    # Handle zero separately
    if num == 0:
        return "Zero"
    
    # Convert to string for easier manipulation
    num_str = str(num)
    
    # Function to convert a number less than 1000 to words
    def convert_less_than_thousand(n):
        if n == 0:
            return ""
        
        if n < 20:
            return ones[n]
        
        if n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
        
        return ones[n // 100] + " Hundred" + (" " + convert_less_than_thousand(n % 100) if n % 100 != 0 else "")
    
    # For Indian system
    words = []
    
    # Handle crores (1,00,00,000 and above)
    if len(num_str) > 7:
        crores = int(num_str[:-7])
        words.append(convert_less_than_thousand(crores) + " Crore")
        num_str = num_str[-7:]
    
    # Handle lakhs (1,00,000 to 99,99,999)
    if len(num_str) > 5:
        lakhs = int(num_str[:-5])
        if lakhs > 0:
            words.append(convert_less_than_thousand(lakhs) + " Lakh")
        num_str = num_str[-5:]
    
    # Handle thousands (1,000 to 99,999)
    if len(num_str) > 3:
        thousands = int(num_str[:-3])
        if thousands > 0:
            words.append(convert_less_than_thousand(thousands) + " Thousand")
        num_str = num_str[-3:]
    
    # Handle last three digits (hundreds, tens, ones)
    if int(num_str) > 0:
        words.append(convert_less_than_thousand(int(num_str)))
    
    return " ".join(words)