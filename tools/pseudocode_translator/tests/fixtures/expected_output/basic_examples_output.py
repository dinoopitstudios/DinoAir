# Expected output for basic_examples.txt


# Basic Function Example
def greet(name):
    """Greet a person with their name."""
    return f"Hello, {name}!"


# Simple Calculator
def calculator(num1, num2, operation):
    """Perform basic arithmetic operations."""
    if operation == "add":
        return num1 + num2
    if operation == "subtract":
        return num1 - num2
    if operation == "multiply":
        return num1 * num2
    if operation == "divide":
        if num2 == 0:
            raise ValueError("Cannot divide by zero")
        return num1 / num2
    raise ValueError(f"Unknown operation: {operation}")


# List Processing
def process_list(numbers):
    """Process a list of numbers and return statistics."""
    if not numbers:
        return {"sum": 0, "average": 0, "min": None, "max": None}

    total = sum(numbers)
    average = total / len(numbers)
    minimum = min(numbers)
    maximum = max(numbers)

    return {"sum": total, "average": average, "min": minimum, "max": maximum}


# String Manipulation
def clean_text(text):
    """Clean text by removing whitespace and special characters."""
    import re

    # Remove leading and trailing whitespace
    text = text.strip()

    # Convert to lowercase
    text = text.lower()

    # Remove special characters
    return re.sub(r"[^a-zA-Z0-9\s]", "", text)


# File Operations
def read_file(filename):
    """Read contents of a file."""
    try:
        with open(filename) as file:
            return file.read()
    except FileNotFoundError:
        return f"Error: File '{filename}' not found"
    except Exception as e:
        return f"Error reading file: {str(e)}"
