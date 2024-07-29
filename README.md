# Pypable: A Toolset for Piping Values and Text Processing

## Introduction

Pypable is a Python package designed to simplify the process of piping values between functions and provide optional shell-like text-processing tools. 

The `PipableMixin` class provides features to make any class pipable, in the style of traditional shells such as Bourne and Zsh.

The package's second most important feature is the `Receiver`, which allows you to easily chain functions and pass values between them.

Additionally, the `Pypable.text` module offers utilities for shell-like text processing and manipulation.

## Installation

To install Pypable, use pip:

```bash
pip install pypable
```

## Usage

### PipableMixin

The `PipableMixin` is the most important tool in Pypable. It allows add pipe-based chaining to all methods of the inheriting class.
Here's an example of how to use it:

```python
from pypable.mixins import Pipable
from pypable.typing import wrap_object

def double(value):
    return value * 2

# Pipe the value 5 to the "double" function
result = wrap_object(5, Pipable) | double
# result = 5 * 2 = 10
```

### Receiver Class

The `Receiver` class is used to create a "receiving" function call. By placing a receiver object on the right side of a pipe, the callable defined in the receiver can be deferred rather than called at time of evaluation. This enables any function or method to receive the value from the left side of a pipe, without needing to create a pipable object.

Here's an example of how to use it:

```python
from pypable.mixins import Receiver

# Create a "receiver-function" by returning a Receiver with the desired operation
def raise_power(value, power):
    return value ** power

# Pipe the value 5 to the receiver object
result = 5 | Receiver(raise_power, 2)

# result = 5 ** 2 = 25
```

Alternatively, a Receiver can be assigned to a variable, and that variable used as the target of a pipe:

```python
from pypable.mixins import Receiver

def add(value, other):
    return value + other

# Create a receiver object with the `add` callable and a fixed value
add_three = Receiver(add, 3)

# Pipe the value 5 to the receiver object
result = 5 | add_three
# result = 5 + 3 = 8
```

### Text Module

The `Pypable.text` module provides utility functions for text processing and manipulation.

```python
from pypable.text import cat, grep, sed

jabberwocky = cat('jabberwocky.txt')
# “Beware the Jabberwock, my son!
# The jaws that bite, the claws that catch!
# Beware the Jubjub bird, and shun
# The frumious Bandersnatch!” 

# Pipe the Text object through the grep function with the argument 'beware'
#   then replace the RegEx pattern `,?\s` with a single underscore
result = jabberwocky | grep('beware') | sed(',?\s', '_') > 'beware.txt'

# The result will be saved into a new file 'beware.txt'
# Output: Beware_the_Jabberwock_my_son!
#         Beware_the_Jubjub_bird_and_shun
```

### Printer Utilities

The `Pypable.printers` module provides some simple methods for printing and decorating multi-line strings.
Here's an example of how to use it:

```python
from pypable.printers import mprint

result = mprint("""
    This is a
        multi-line
    string.
    """)
# This is a
#     multi-line
# string.
```

In this example, we also show that the mprint has a unique style of dedenting that uses the whitespace of the final line (`    """`) as a guide for how much whitespace to remove. If the final line does not consist solely of horizontal whitespace, then the `textwrap.dedent()` function is used instead.

### Pypable Typing

Finally, the `Pypable.typing` module provides a few additional tools that may be useful outside of piping context.

Some of the available functions include:

- `isinstance(obj, types)`: A replacement for the built-in _isinstance_, this function accepts subscripted types and type-tuples.
- `get_parent_class(obj)`: Returns the class that an instance belongs to. This works even on builtins and nested classes. This is especially useful for determining the parent class of a method, where the `__class__` attribute would typically return a `method_descriptor` type.
- `wrap_object(obj, *mixins, attrs)`: Dynamically cast an object as a subclass that includes the `mixins`.
- `class_path(obj)`: Get the fully qualified name of the class that `__obj` belongs to, e.g. `class_path(Text())` returns `"Pypable.text.Text"`.


Here's an example of how to use these functions:

<-- TODO: add some examples -->
```python
```

## License

Pypable is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.