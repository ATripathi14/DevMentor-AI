# Syntax_Error Script -violation of the formal lexical and structural grammar rules specified by a programming language.

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    return a / b

print("Select Operation")
print("1. Add")
print("2. Subtract")
print("3. Multiply")
print("4. Divide")

choice = input("Enter choice (1/2/3/4): ")

num1 = float(input("Enter first number: "))
num2 = float(input("Enter second number: "))

if choice =='1':
    add(num1,num2)
elif choice == '2':
    subtract(num1,num2)
elif choice == '3':
    multiply(num1,num2)
elif choice == '4':
    divide(num1,num2)
# missed colon after else led to syntax error
else                            
    print("Invalid input")