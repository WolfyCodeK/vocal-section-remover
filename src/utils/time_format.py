def format_time(seconds):
    """Format time in MM:SS format"""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02}:{secs:02}"

def format_time_precise(seconds):
    """Format time with decimal precision"""
    minutes = int(seconds) // 60
    secs = seconds % 60
    return f"{minutes:02}:{secs:05.2f}" 