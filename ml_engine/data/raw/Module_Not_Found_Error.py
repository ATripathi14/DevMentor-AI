#module_not_found — importing a package that isn't installed

from prettytable import PrettyTable #prettytable module is not installed on the system
table = PrettyTable(["Name", "Age"])
table.add_row(["Alice", 25])
table.add_row(["Bob", 30])
print(table)

