# permission_error — writing to a read-only file/protected directory

import os
import stat
def write_to_locked_file():
    file = open("readonly.txt", "w")
    file.write("hello")
    file.close()

# create the file
with open("readonly.txt", "w") as f:
    f.write("original content")

# make it read-only
os.chmod("readonly.txt", stat.S_IREAD)

# now try to write to it -> PermissionError
write_to_locked_file()