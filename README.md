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

<-- TODO ADD EXAMPLE -->
```python
```

### Receiver Class

<-- TODO word this better -->
The `Receiver` class is used to create a "receiving" function call. By placing a receiver object on the right side of a pipe,
the callable defined in the receiver can be deferred rather than called at time of evaluation.
This enables any function or method to receive the value from the left side of a pipe, without needing to create a pipable object.

<-- TODO: example -->

### Text Module

The `Pypable.text` module provides utility functions for text processing and manipulation. Here's an example of how to use it:

```python
from Pypable.text import Text, grep

example = Text("""
“Beware the Jabberwock, my son!
The jaws that bite, the claws that catch!
Beware the Jubjub bird, and shun
The frumious Bandersnatch!” 
""")

example | grep('beware', insensitive=True) | print
# Beware the Jabberwock, my son!
# Beware the Jubjub bird, and sun
```

In this example... <TODO>

### Printer Utilities

The `Pypable.printers` module provides some simple methods for printing and decorating multi-line strings.
Here's an example of how to use it:

```python
from Pypable.printers import mprint

text = """This is a
multi-line
string."""

mprint("""
    This is a
        multi-line
    string.
    """)
# This is a
#   multi-line
# string.
```

In this example... <TODO>
Notice that the second line is indented, while the other two lines have had their indents removed.
When printing with `mprint`, if the final line consists of only horizontal whitespace, that whitespace will be used for dedenting.
Otherwise, the text will be dedented in the style of the [textwrap](https://docs.python.org/3/library/textwrap.html#textwrap.dedent) module.

### Pypable Typing

Finally, the `Pypable.typing` module provides a few additional tools that may be useful outside of piping context.
Some of these functions include:

- `isinstance`: A replacement for the built-in _isinstance_, this function accepts subscripted types and type-tuples.
- `class_path`: Checks if an object is callable.
- `extend_class`: Checks if an object is iterable.

Here's an example of how to use these functions:

<-- TODO -->
```python
```

In this example...

## License

Pypable is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.