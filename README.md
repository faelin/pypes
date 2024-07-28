# Pypable: A Toolset for Piping Values and Text Processing

## Introduction

Pypable is a Python package designed to simplify the process of piping values between functions and provide optional shell-like text-processing tools. 

The package's primary feature is the `Receiver`, which allows you to easily chain functions and pass values between them.

The `PipableMixin` class provides features to make any class pipable, in the style of traditional shells such as Bourne and Zsh.

Additionally, the `Pypable.text` module offers utilities for shell-like text processing and manipulation.

## Installation

To install Pypable, use pip:

```bash
pip install pypable
```

## Usage

### Receiver Class



### PipableMixin

The `PipableMixin` is the most important tool in Pypable. It allows you to chain methods and pass values between them seamlessly.
Here's an example of how to use it:

<-- TODO: fix this example -->
```python
from Pypable.mixins import PipableMixin

class MyClass(PipableMixin):
    def double(self, value):
        return value * 2

    def triple(self, value):
        return value * 3

# Create an instance of MyClass
my_instance = MyClass()

# Chain functions and pass values
result = my_instance | double | triple(5)
print(result)  # Output: 15
```

In this example, we define a class `MyClass` that inherits from `PipableMixin`.
We then define two methods, `double` and `triple`, which take a value and perform some operation on it.
Finally, we create an instance of `MyClass` and chain the `double` and `triple` methods using the pipe operator (`|`).
The result is the final output of the chained functions. <-- TODO: CURRENTLY THIS EXAMPLE DOES NOT WORK -->

### Text Module

The `Pypable.text` module provides utility functions for text processing and manipulation. Here's an example of how to use it:

<-- TODO fill in this example -->
```python
```

In this example, we...

### Printer Utilities

The `Pypable.printers` module provides some simple methods for printing and decorating multi-line strings.
<-- TODO: expand this -->

### Pypable Typing

Finally, the `Pypable.typing` module provides a few additional tools that may be useful outside of piping context.
These functions include...
<-- TODO: expand this -->

## License

Pypable is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.