# logger_utils.py
import config

def print_info(*args, sep=' ', end='\n'):
    print("\033[37mℹ️ ", end='')       # White info icon start
    print(*args, sep=sep, end='')
    print("\033[0m", end=end)

def print_warning(*args, sep=' ', end='\n'):
    print("\033[33m⚠️ ", end='')       # Yellow warning icon start
    print(*args, sep=sep, end='')
    print("\033[0m", end=end)

def print_error(*args, sep=' ', end='\n'):
    print("\033[31m❌ ", end='')       # Red error icon start
    print(*args, sep=sep, end='')
    print("\033[0m", end=end)

def print_debug(*args, sep=' ', end='\n'):
    if config.DEBUG_ENABLED:
        print("\033[36m🐞 ", end='')   # Cyan debug icon start
        print(*args, sep=sep, end='')
        print("\033[0m", end=end)