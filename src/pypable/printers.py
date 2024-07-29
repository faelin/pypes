import builtins
import re
import textwrap
from typing import IO, Any

from pypable.typing import isinstance
from pypable.typing import PathLike, Destination, OpenMode


# noinspection PyShadowingBuiltins
def print(*values, file:Destination = None, mode:OpenMode = 'w', **kwargs):
	""" Prints the values to a file or stream if specified, or to sys.stdout by default.

    Keyword Arguments:
    	file: a file-like object (stream), or a file-path; defaults to the current sys. stdout.
    	sep: string inserted between values, defaults to a space.
    	end: string appended after the last value, defaults to a newline.
    	flush: whether to forcibly flush the stream.
	"""

	if file is None:
		return builtins.print(*values, **kwargs)
	if isinstance(file, IO):
		return builtins.print(*values, file=file, **kwargs)
	elif isinstance(file, PathLike):
		with open(file, mode) as file: return builtins.print(*values, file=file, **kwargs)
	else:
		raise TypeError(f"invalid destination type '{file.__class__}'")


def tee(file:Destination = None, *message:Any, mode:OpenMode = 'w', end:str = '\n', stdout = True):
	"""
	Mimics the shell utility 'tee'.

	This function prints the given message to the standard output and optionally to a specified destination.

	Parameters:
		file: The optional file or file-like object to which the message will be printed. If not provided, the message will only be printed to the standard output.
		message: The message to be printed. If provided as a sequence of strings, it will be joined with the 'end' character.
		mode: The mode in which the destination file will be opened. Defaults to 'w' (write).
		end: The character to be used as the end of each line in the message. Defaults to '\\n' (newline).
		stdout: If false, message is not printed to console.

	Returns:
		None: This function does not return any value. It only prints the message to the standard output and the specified destination.
	"""

	if stdout: print(message, sep=end, end=end)
	if file:   print(message, sep=end, end=end, file=file)

	return message


def mprint(*strings, ending:str = '\n', indent:bool = False, file:Destination = None):
	"""
	Prints the given strings with optional line-end and indentation.

	This function takes a variable number of strings as input and prints them to the standard output.
	The strings can be joined with the specified 'end' character.

	Parameters:
		*strings: A variable number of strings to be printed.
		ending: The character to be used as the end of each line in the strings. Defaults to '\\n' (newline).
		indent: A boolean flag indicating whether indents in the string should be prerserved. Defaults to False.
		file: Optional, a file to print to.

	Returns:
		None: This function does not return any value. It only prints the strings to the standard output.
	"""

	strings = [str(line) for line in strings]
	text = ending.join([str(line) for line in strings]) if indent else dedent(*strings)
	text = text.removesuffix('\n').removeprefix('\n')
	print(text, file=file)


def dedent(*strings:str, ending:str = '\n'):
	"""
	Dedents the given strings by removing leading whitespace from each line.

	By default, only leading whitespace that appears at the beginning of *every* line will be considered.
	(See the textwrap.dedent documentation for more information)

	If the final line of the string contains only whitespace,this will be used as the template whitespace for dedenting.
	This feature is primarily intended for use with triple-quoted multiline strings.

	Examples:
		1. Dedent a list of strings with inconsistent leading whitespace:
		::
			>>> print(dedent("This is a test\\n", "    Another test\\n"))
			This is a test
			   Another test

		2. Multiline strings can be used to improve legibility of code:
		::
			>>> print(dedent('''
			... 	This is a multiline string
			... 	That will be magically un-indented!
			... '''))
			This is a multiline string
			That will be magically un-indented!

		3. When using multiline strings, add a '\' at the end of the first line to add an opening blank line:
		::
			>>> print('---')
			... print(dedent('''\
			... 	There will be a blank line before this line!
			... '''))
			... print('---')
			---

			There will be a blank line before this line!

			---

		4. Only shared indentation is removed:
		::
			>>> print(dedent(
			... 	'''
			... 	INDENTED STRING:
			... 	      sub-indented string
			... 	'''
			... ))
			INDENTED STRING:
				  sub-indented string

		5. If the final line is composed only of whitespace, that whitespace
		is used as the template for indentaion removal:
		::
			>>> print(dedent('''
			...         This is a multiline string
			...         But the indentation will be preserved!!
			... 	'''))
				This is a multiline string
				But the indentation will be preserved!!


	Parameters:
		strings (str): A sequence of strings to be dedented.
		ending (str): The character or characters to be used as the end of each line in the strings. Defaults to '\\n' (newline).

	Returns:
		str: A string containing the dedented version of the input strings.
	"""

	text = ending.join(strings)
	match = re.search('^([ \t]+)\Z', text, flags = re.MULTILINE)
	if match:  # obtain the horizontal whitespace indent of the final line
		indent = match.group()
		return re.sub(f'^{indent}', '', text, flags = re.MULTILINE)  # strip {indent} from the beginning of each line
	else:
		return textwrap.dedent(text)


def box(*strings:str, width:int = None, indent = False, title:str = None, **kwargs):
	"""
	Prints the given strings within a box.

	This function takes a variable number of strings as input and prints them within a box.
	The strings can be whitespace-padded to an optional width (left-justified)

	Parameters:
		*strings (str): A variable number of strings to be printed within the box.
		width (int): Optional width of the box. If not provided, the width will be automatically calculated based on the longest string.
		indent (bool): A boolean flag indicating whether indents in the string should be preserved. Defaults to False.
		title (str): A string to use as a title. This string will be center justified.

	Keyword Arguments:
		border (str): The character to be used for the border. Defaults to '*' (asterisk).
		corner (str): The character to be used for the four corner positions. Defaults to the value of 'border'.
		horz (str): The character to be used for the horizontal border. Defaults to the value of 'border.
		vert (str): The character to be used for the vertical border. Defaults to the value of 'border.
		top (bool): Flag, whether to print the top border. Defaults to True.
		bot (bool): Flag, whether to print the bottom border. Defaults to True.
		ul (str): The character to be used for upper-left corner. Defaults to the value of 'corner'.
		ur (str): The character to be used for upper-right corner. Defaults to the value of 'corner'.
		ll (str): The character to be used for lower-left corner. Defaults to the value of 'corner'.
		lr (str): The character to be used for lower-right corner. Defaults to the value of 'corner'.
		pad (int): The number of whitespace character to surround the text inside of the order. Defaults to 1.
		margin (int): The number of whitespace character to surround the entire box with. Defaults to 0.

	Returns:
		None: This function does not return any value. It only prints the strings within the box to the standard output.
	"""

	border = kwargs.get('border', '*')
	corner = kwargs.get('corner', border)
	horz = kwargs.get('horz', border)
	vert = kwargs.get('vert', border)
	top = kwargs.get('top', True)
	bot = kwargs.get('bot', True)
	ul = kwargs.get('ul', corner)
	ur = kwargs.get('ur', corner)
	ll = kwargs.get('ll', corner)
	lr = kwargs.get('lr', corner)
	pad = kwargs.get('pad', 1)
	margin = kwargs.get('margin', 0)

	strings = ('\n'.join(strings) if indent else dedent(*strings)).splitlines()
	colwidth = width or max(len(s) for s in strings) + pad*2
	fullwidth = colwidth + len(vert)*2
	maxlen = colwidth - pad*2
	side_margin = ' '*margin

	# noinspection PyShadowingBuiltins
	text = []
	def _print(string): text.append(side_margin+string+side_margin)

	for _ in range(int(margin/3)): _print(' '*fullwidth)  # whitespace margin above box
	if top: _print(ul + horz*colwidth + ur)  # print top border
	for _ in range(int(pad/4)): _print(vert + ' '*colwidth + vert)  # whitespace padding above text
	if title:
		for line in title.splitlines(): _print(vert + '\033[1m' + line.center(colwidth) + '\033[0m' + vert)  # print title line with BOLD ('\033[1m') formatting
	for line in strings: _print(vert + ' '*pad + '%-*.*s'%(maxlen, maxlen, line) + ' '*pad + vert)  # print the main text body
	for _ in range(int(pad/4)): _print(vert + ' '*colwidth + vert)  # whitespace padding below text
	if bot: _print(ll + horz*colwidth + lr)  # print bottom border
	for _ in range(int(margin/3)): _print(' '*fullwidth)  # whitespace margin below box

	return '\n'.join(text)


def boxprint(*args, **kwargs):
	"""
	Prints the given strings within a box.

	This function takes a variable number of strings as input and prints them within a box.
	The strings can be whitespace-padded to an optional width (left-justified)

	Parameters:
		*strings (str): A variable number of strings to be printed within the box.
		width (int): Optional width of the box. If not provided, the width will be automatically calculated based on the longest string.
		indent (bool): A boolean flag indicating whether indents in the string should be preserved. Defaults to False.
		title (str): A string to use as a title. This string will be center justified.

	Keyword Arguments:
		border (str): The character to be used for the border. Defaults to '*' (asterisk).
		corner (str): The character to be used for the four corner positions. Defaults to the value of 'border'.
		horz (str): The character to be used for the horizontal border. Defaults to the value of 'border.
		vert (str): The character to be used for the vertical border. Defaults to the value of 'border.
		top (bool): Flag, whether to print the top border. Defaults to True.
		bot (bool): Flag, whether to print the bottom border. Defaults to True.
		ul (str): The character to be used for upper-left corner. Defaults to the value of 'corner'.
		ur (str): The character to be used for upper-right corner. Defaults to the value of 'corner'.
		ll (str): The character to be used for lower-left corner. Defaults to the value of 'corner'.
		lr (str): The character to be used for lower-right corner. Defaults to the value of 'corner'.
		pad (int): The number of whitespace character to surround the text inside of the order. Defaults to 1.
		margin (int): The number of whitespace character to surround the entire box with. Defaults to 0.

	Returns:
		None: This function does not return any value. It only prints the strings within the box to the standard output.
	"""

	print(box(*args, **kwargs))
boxprint.__doc__ = box.__doc__