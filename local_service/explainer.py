# Maps each of the 12 official error categories to a plain-English
# explanation and suggested fix, shown to the user by the /analyze endpoint
EXPLANATIONS = {
    "syntax_error": "Python couldn't even start running your code because something breaks its grammar rules — usually a missing colon, an unclosed bracket or quote, or bad indentation. Look at the exact line and column the error points to; the mistake is almost always right there or on the line just before it.",

    "type_error": "You tried to combine or use two things that don't work together — like adding a number and a piece of text, or calling something that isn't actually a function. Check the types of the values involved right before that line (you can use type(x) to check) and make sure they match what the operation expects.",

    "none_type_error": "A variable that should have held a real value turned out to be None (empty), and then your code tried to use it anyway — like calling .upper() on it or looping over it. Trace back to where that variable was set and figure out why it ended up empty instead of holding real data.",

    "key_error": "You tried to look up a key in a dictionary that doesn't actually exist there — like dict['user_id'] when 'user_id' was never added. Double-check the exact spelling and case of the key, or use dict.get('key') instead, which returns None instead of crashing if the key is missing.",

    "index_error": "You tried to grab an item at a position that doesn't exist in your list or sequence — like asking for the 5th item in a 3-item list. Check the actual length of the list with len() right before you index into it, especially if the list's size can change.",

    "attribute_error": "You tried to use a method or property that this object doesn't actually have — like calling .append() on something that isn't a list. Print the object or check type(object) to see what it really is, and confirm the method name is spelled correctly for that type.",

    "module_not_found": "Python looked for a package you tried to import and couldn't find it installed anywhere it knows to look. Run pip install <package_name> in your active environment — and make sure you're in the right conda/virtual environment when you do it.",

    "file_not_found": "Your code tried to open a file at a path that doesn't exist, at least from where the script is actually running. Print the exact path being used and check it against your file explorer — a common cause is running the script from a different folder than you expect.",

    "permission_error": "The operating system blocked your program from opening or modifying a file — often because the file is marked read-only, or another program currently has it open. Check the file's permissions, close any other program that might be using it, and confirm you have write access to that folder.",

    "value_error": "Something like int('abc') failed — the value you passed is technically the right type, but not in a format the function can actually work with. Check exactly what value is being passed at that line and confirm it's in the shape the function expects.",

    "network_error": "Your program tried to reach a server or address and couldn't connect — the target might be down, the address might be wrong, or your internet connection might be the issue. Confirm the URL or host/port is correct, and test whether you can reach it another way (like a browser or ping).",

    "other_error": "This error doesn't match one of the common categories above. Read the full traceback carefully — the last line usually names the exact exception type, and the lines above it show exactly which part of your code triggered it.",
}

# Maps raw Python exception class names (as extracted by parse_error())
# to one of the 12 official category labels above. Falls back to
# "other_error" for any unrecognized exception type.
ERROR_TYPE_TO_CATEGORY = {
    "SyntaxError": "syntax_error",
    "TypeError": "type_error",
    "KeyError": "key_error",
    "IndexError": "index_error",
    "AttributeError": "attribute_error",
    "ModuleNotFoundError": "module_not_found",
    "FileNotFoundError": "file_not_found",
    "PermissionError": "permission_error",
    "ValueError": "value_error",
    "ConnectionError": "network_error",
    "requests.exceptions.ConnectionError": "network_error",
    "ZeroDivisionError": "other_error",
}

def normalize_error_type(raw_error_type: str) -> str:
    """Maps a raw Python exception class name to one of the 12 official category labels."""
    return ERROR_TYPE_TO_CATEGORY.get(raw_error_type, "other_error")