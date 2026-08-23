EXPLANATIONS = {
    "syntax_error": "Your code has a typo or structural mistake — like a missing colon, unmatched bracket, or incorrect indentation. Check the exact line number in the error for the mistake.",
    "type_error": "You tried to use a value in a way that doesn't match its type — for example, adding a number to a string. Check what type each variable actually is before the operation.",
    "none_type_error": "You tried to use a variable that is None (empty) as if it held a real value. Trace back to where the variable was assigned and check why it ended up as None.",
    "key_error": "You tried to access a dictionary key that doesn't exist. Double-check the exact spelling of the key, or use .get() with a default value to avoid crashing.",
    "index_error": "You tried to access a list or sequence position that's out of range. Check the actual length of the list before indexing into it.",
    "attribute_error": "You tried to use a method or property that doesn't exist on that object. Check the object's actual type and what attributes it really has.",
    "module_not_found": "Python couldn't find a module you tried to import. Make sure it's installed in your active environment (pip install <module_name>).",
    "file_not_found": "The program tried to open a file that doesn't exist at that path. Double-check the file path and that the file actually exists there.",
    "permission_error": "Your program doesn't have permission to access or modify this file. Check the file's permissions, or whether another program has it locked.",
    "value_error": "A function received a value of the right type but an inappropriate value — for example, trying to convert 'abc' to a number. Check the actual value being passed in.",
    "network_error": "The program couldn't establish a network connection. Check your internet connection, or whether the target server/port is actually reachable.",
    "other_error": "An error occurred that doesn't match a common category. Read the full traceback for more specific detail about what went wrong.",
}

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
    "ZeroDivisionError": "other_error",
}


def normalize_error_type(raw_error_type: str) -> str:
    """Maps a raw Python exception class name to one of the 12 official category labels."""
    return ERROR_TYPE_TO_CATEGORY.get(raw_error_type, "other_error")