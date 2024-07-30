import os
import re
from typing import overload
from typing import Sequence, Callable, IO, SupportsIndex, Union, Iterator
from pathlib import Path
from collections import OrderedDict

from pypable.typing import isinstance
from pypable.typing import PathLike, Destination, PatternLike, StringList, OpenMode, LineIdentifier, RegexFlag
from pypable.mixins import Pipable, Receiver, Placeholder
from pypable.printers import print


class Text(Pipable, list[str]):
	"""
	A Text object is a thinly-wrapped list of strings.

	The Text class is an interface around a list of strings, exposing additional text-manipulation tools
	to quickly filter, sort, search, transform, and modify the text. Each string in the list represents a single
	line of text, without line-endings. Line-endings are applied when converting the Text object to a string.

	Text objects inherit most of the methods of the underlying base-class (str). Therefore, any method
	that could be used to modify, inspect, or search a string can be applied to a Text object.
	"""

	# === INTERNAL METHODS ===

	def __init__(self, source:Union[PathLike, StringList, Iterator[str]] = None, end:str = '\n', flatten = True):
		"""
		Parameters:
			source: Either a file-path to load as a Text object, or a list of strings to be treated as lines of text.
			end: The default end to apply when converting the Text() object into a single contiguous string.
			flatten: Split input lines on ``end``. Defaults to True.
		"""

		self.end = end

		if source is None:
			lines = []
		elif isinstance(source, str) and end in source:
			lines = source.split(end)
		elif isinstance(source, PathLike):  # if PathLike
			lines = Path(source).read_text().split(end)
		elif isinstance(source, StringList) or isinstance(source, Iterator):
			if flatten:
				lines = self._flatten([str(string).split(end) for string in source])
			else:
				lines = [str(string) for string in source]
		else:
			raise TypeError('source must be a file-path or a list of strings')

		super().__init__(lines)

	def __lt__(self, value): return NotImplemented

	def __str__(self): return self.end.join(self)  # join each entry with the implicit line-ending

	def __contains__(self, key): return self.contains(key)

	def __copy__(self): return type(self)(super().copy(), end=self.end)

	def __reversed__(self): return type(self)( list(super().__reversed__()) )

	def __getitem__(self, __i:SupportsIndex): return type(self)( super().__getitem__(__i), end=self.end )

	def __format__(self, format_spec): return str( self.transform(str.__format__, format_spec, suppress_errors=(TypeError,), inplace=False) )

	def __mod__(self, __value:Union[str,tuple[str]]): return self.transform(str.__mod__, __value, suppress_errors=(TypeError,), inplace=False)

	def __imod__(self, __value:Union[str,tuple[str]]): return self.transform(str.__mod__, __value, suppress_errors=(TypeError,))

	def __add__(self, other:Union[Sequence,str]):
		""" Return a Text object with the contents of ``other`` appended. """
		if isinstance(other, str):
			return super().__add__(other.split(self.end))
		if isinstance(other, list):
			return super().__add__(list(other))
		else:
			raise TypeError(f'can only concatenate Text, list, or str to text -- invalid type {other.__class__.__name__}')


	def __iadd__(self, other:Union[Sequence,str]):
		""" Append ``other`` to the text. """
		if isinstance(other, str):
			return super().__iadd__(other.split(self.end))
		if isinstance(other, list):
			return super().__iadd__(list(other))
		else:
			raise TypeError(f'can only concatenate Text, list, or str to text -- invalid type {other.__class__.__name__}')


	def __radd__(self, other):
		""" Add self to ``other``. """
		if hasattr(other, '__add__'):
			return other + type(other)( list(self) )
		else:
			return other + str(self)

	def __lshift__(self, path:PathLike):
		""" Appends the contents of a file to self. """
		if isinstance(path, PathLike):
			return self + type(self)(path, self.end)
		else:
			return NotImplemented


	def __eq__(self, other):
		if isinstance(other, type(self)) and hasattr(other, 'end'):
			return super().__eq__(other) and self.end == other.end
		else:
			return False


	def __ne__(self, other):
		if isinstance(other, type(self)) and hasattr(other, 'end'):
			return super().__ne__(other) or self.end != other.end
		else:
			return True


	# === STATIC METHODS ===

	@staticmethod
	def _flatten(xss): return [x for xs in xss for x in xs]

	@staticmethod
	def _call_transform(__callable: Callable, __obj, *args, suppress_errors = (), **kwargs):
		"""
		Internal method used to apply a transform to an object.

		If a method is supplied, ``__obj`` will first be converted to an appropriate type for the method.
		If args are included, then either the args or kwargs must include a :py:class:`Placeholder` type

		Parameters:
			__callable: Method or function to apply.
			__obj: Object to be transformed.
			suppress_errors: Suppress errors during transform operation (returns __obj instead).
				Defaults to False.
			*args: Arguments to be sent to the transform.
			**kwargs: Keyword-arguments to be sent to the transform.

		Returns:
			The result of the transform, or the value of ``__obj`` if the transform returned `None`.
		"""

		try:
			# noinspection PyUnresolvedReferences
			result = __class__._call_upon(__callable, __obj, *args, **kwargs)
		except suppress_errors as ex:
			result = None

		return result or __obj


	# === FILTER METHODS ===

	def grep(self, pattern:PatternLike, insensitive = False, invert = False, flags:Union[int,RegexFlag] = 0):
		"""
		Filters the lines of the Text object based on a given pattern.

		Parameters:
			pattern: The pattern to search for in the lines of the Text object.
			insensitive: If True, the search will be case-insensitive. Defaults to False.
			invert: If True, the function will return lines that do *not* match the pattern. Defaults to False.
			flags: Flags to be passed to the regular-expression engine. Defaults to 0.

		Returns:
			A new Text object containing the lines that match the specified pattern.
		"""

		if insensitive: flags = flags | re.I
		return type(self)( [line for line in self if invert ^ bool(re.search(pattern, line, flags=flags))], self.end )


	def lines_between(self, start:PatternLike = None, end:PatternLike = None, invert = False, flags:Union[int,RegexFlag] = 0):
		"""
		Extracts lines between two patterns from a given file.
		Works similarly to the sed operation 'sed -n "/$start/,/$end/p" $file'

		Lines are returned starting with the line that matches the ``start`` pattern,
		continuously until (and including) the line that matches the ``end`` pattern.
		If the ``end`` pattern is never matched, then all remaining lines are matched.

		The ``start`` pattern may be matched multiple times. Each subsequent start-end block
		is appended to the returned lines.

		Parameters:
			start: Optional, the start pattern to search for in the text.
				If omitted, all lines until the ``end`` pattern will be matched.
			end: Optional, the end pattern to search for in the text.
				If omitted, all lines after the ``start`` pattern will be matched.
			invert: If True, only lines that are *not* matched are returned. Defaults to False.
			flags: Flags to be passed to the regular-expression engine. Defaults to 0.

		Returns:
			A new Text object containing all the lines between the specified start and end patterns.
		"""

		lines = []
		begin = None if start is not None else 0

		for i, line in enumerate(self):
			if begin is None:  # if we haven't started matching yet...
				if start is not None and re.search(start, line, flags):
					begin = i  # begin matching...
				elif invert:
					# if we are in "invert" mode, append every line that is not inside of the begin-block
					lines.append(line)
			elif end is not None and re.search(end, line, flags):
				if not invert:
					# if we are NOT in "invert" mode, append lines between the 'start' and 'end' patterns (inclusive)
					lines += self[begin:i]
				begin = None  # end matching...

		# if we found the start-pattern but never found the end-pattern, append all remaining lines
		if begin and not invert:
			lines += self[begin:]

		return type(self)(lines, self.end)


	def unique(self):
		""" Returns a new Text object containing only the unique lines from the original Text object.
		Preserves the order of lines in the text.
		"""
		return type(self)(OrderedDict.fromkeys(self).keys(), end=self.end)


	# === TRANSFORM METHODS ===
	# methods for modifying the contents of the Text object.

	def transform(
			self,
			func: Callable,
			*args,
			start: LineIdentifier = None,
			end: LineIdentifier = None,
			invert = False,
			match_flags: RegexFlag = 0,
			flatten = True,
			inplace = False,
			**kwargs
			):
		"""
		Applies a transformation function to each line in the text.

		Parameters:
			func: A callable function that will be applied to each line.
			start: The start pattern to search for in the text.
			end: The end pattern to search for in the text.
			invert: If True, only lines that are *not* matched are returned. Default is False.
			match_flags: Regex flags to use when looking for the `start` or `end` patterns.
			inplace: Transforms the object in-place. Default is False.
			flatten: Passed to the constructor, determines if the text should be further split.
				Only useful if ``inplace`` is False.
			*args: Additional positional arguments to be passed to the specified function.
			**kwargs: Additional keyword arguments to be passed to the specified function.
				If kwargs are needed that conflict with the named parameters above,
				they can be provided in a dictionary parameter named `kwargs` (see below).

		Keyword Arguments:
			suppress_errors: List of exceptions to ignore during the transform.
				When an exception in the list is encountered, the current line will be left untransformed.
				See :py:meth:`Text._call_transform` for more information.
			kwargs: Dictionary to be passed as additional kwargs to the transform function.
				Use this to specify kwargs that conflict with the named parameters of this function.

		Returns:
			A new Text object where all lines have been transformed according to the specified function and arguments.
		"""

		kwargs.update(kwargs)
		kwargs.pop('kwargs', None)

		if not (start or end):
			# if no `start` or `end`, process every line
			lines = [type(self)._call_transform(func, line, *args, **kwargs) for line in self]

		else:
			lines = []
			in_block = False

			for i, line in enumerate(self):
				# if we are inside a match-block...
				if in_block:
					# if `end` is an index or line matches the `end` pattern...
					if i == end or re.search(end, line, match_flags):
						in_block = False  # end match-block

					# and...
					if not invert:
						# transform lines that are inside of the match-block
						line = type(self)._call_transform(func, line, *args, **kwargs)

				# if we haven't found a match-block yet...
				else:
					# if `start` is an index or this line contains the `start` pattern...
					if i == start or re.search(start, line, match_flags):
						in_block = True  # begin match-block

						# transform the matched line if we are not inverted
						if not invert:
							line = type(self)._call_transform(func, line, *args, **kwargs)

					# otherwise...
					if invert:
						# transform lines that are *not* inside of the match-block
						line = type(self)._call_transform(func, line, *args, **kwargs)

				# finally, append the current line, whether or not it was modified
				lines.append(line)

		if inplace:
			self[:] = lines
			return self
		else:
			return type(self)(lines, end=self.end, flatten=flatten)


	def encode(self, encoding:str = "utf-8", errors:str = "strict", **kwargs):
		"""
		Encode the Text object using the codec registered for encoding.
		The :py:attr:`end` attribute will also be encoded.

			encoding
				The encoding in which to encode the lines of the Text object.
			errors
				The error handling scheme to use for encoding errors.
				The default is 'strict' meaning that encoding errors raise a
				UnicodeEncodeError.  Other possible values are 'ignore', 'replace' and
				'xmlcharrefreplace' as well as any other name registered with
				codecs.register_error that can handle UnicodeEncodeErrors.
		"""

		self.end = self.end.encode(encoding, errors)
		return self.transform(str.encode, encoding, errors, **kwargs)


	def decode(self, encoding:str = "utf-8", errors:str = "strict", **kwargs):
		"""
		Encode the Text object using the codec registered for encoding.
		The :py:attr:`end` attribute will also be encoded.

			encoding
				The encoding in which to decode the lines of the Text object.
			errors
				The error handling scheme to use for decoding errors.
				The default is 'strict' meaning that decoding errors raise a
				UnicodeEncodeError.  Other possible values are 'ignore', 'replace' and
				'xmlcharrefreplace' as well as any other name registered with
				codecs.register_error that can handle UnicodeEncodeErrors.
		"""

		if isinstance(self.end, bytes): self.end = self.end.decode(encoding, errors)
		return self.transform(bytes.decode, encoding, errors, **kwargs)

	# --- add strings ---

	def prefix(self, string:str, **kwargs):
		""" Add a prefix to each line of the text.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(lambda line : string + line, **kwargs)

	def suffix(self, string:str, **kwargs):
		""" Add a suffix to each line of the text.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""

		# don't flatten the new Text if the suffix ends with the Text line-endings.
		flatten = not string.endswith(self.end)
		return self.transform(lambda line : line + string, **kwargs, flatten=flatten)

	def zfill(self, width:SupportsIndex, **kwargs):
		""" Left-pad each line with zeroes, to the given width.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.zfill, width, **kwargs)

	# --- remove strings ---

	def strip(self, chars:str = None, **kwargs):
		""" Removes leading and trailing whitespace from each line.
		If `chars` is given, remove any characters found in `chars` instead.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.strip, chars, **kwargs)

	def lstrip(self, chars:str = None, **kwargs):
		""" Removes leading whitespace from each line.
		If `chars` is given, remove any characters found in `chars` instead.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.lstrip, chars, **kwargs)

	def rstrip(self, chars:str = None, **kwargs):
		""" Removes trailing whitespace from each line.
		If `chars` is given, remove any characters found in `chars` instead.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.rstrip, chars, **kwargs)

	# --- change case ---

	def casefold(self, **kwargs):
		""" Return a version of the Text object suitable for caseless comparisons.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.casefold, **kwargs)

	def title(self, **kwargs):
		""" Converts the first character of each word to upper case.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.title, **kwargs)

	def capitalize(self, **kwargs):
		""" Capitalize the first character of each line, and make all other characters lowercase.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.capitalize, **kwargs)

	def upper(self, **kwargs):
		""" Converts each line to upper case.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.upper, **kwargs)

	def lower(self, **kwargs):
		""" Converts the text into lower case.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.lower, **kwargs)

	def swapcase(self, **kwargs):
		""" Swaps cases: lower case characters becomes upper case and vice versa.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.swapcase, **kwargs)

	# --- replace characters ---

	def expandtabs(self, tabsize = 8, **kwargs):
		""" Expands each tab in the text into the number of spaces given by ``tabsize`` (default is 8).

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.expandtabs, tabsize, **kwargs)

	def format(self, *args, **kwargs):
		""" Formats specified values in the text. This method is especially useful for templating.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.format, *args, **kwargs)

	def format_map(self, mapping, **kwargs):
		""" Formats specified values in the text, using subsitutions from the provided mapping.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.format_map, mapping, **kwargs)

	def replace(self, old, new, count = -1, limit = None, **kwargs):
		"""
		Returns a Text object where each instance of the `old` string is replaced with the `new` string.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.

		Parameters:
			old: The string to look for in the text.
			new: The string to replace the matched text with. If blank, the matched text will simply be removed.
			count: Optional, only the first `count` occurrences in each line will be replaced.
				-1 (the default value) means replace all occurrences.
			limit: Optional, only the first `limit` lines containing the ``old`` string will be modified.
				Ignored if not a positive integer.
			start: Optional, the start point (index or pattern) to search for in the text.
			end: Optional, the end point (index or pattern) to search for in the text.
		"""

		# noinspection PyGlobalUndefined
		global __found
		__found = 0

		# noinspection PyShadowingNames
		def replace_in_line(line:str, old:str, new:str, count:int = -1, limit:int = None) -> str:
			""" Inline function used to replace text in a string.

			Args:
				line: The string to be modified.
				old: Pattern to replace.
				new: Pattern to replace it with.
				count: How many instances of the pattern to replace per line.
				limit: The total number of lines that should be replaced.
					This refers to the `_Text__found` global variable used by the :py:meth:`Text.replace` method,
					which is reset each time a call is made to the method.

			Returns:
				The modified string.
			"""

			if limit > 0:
				# noinspection PyGlobalUndefined
				global __found
				if __found < limit:
					__found += 1
					return line.replace(old, new, count)
			else:
				return line.replace(old, new, count)

		return self.transform(replace_in_line, Placeholder, old, new, count, limit, **kwargs)


	def translate(self, table, **kwargs):
		""" Translate each line of the text, according to the translation table.
		``table`` must be a mapping of Unicode ordinals to Unicode ordinals, strings, or None.
		The table must implement lookup/indexing via __getitem__, for instance a dictionary or list.
		If this operation raises LookupError, the character is left untouched.
		Characters mapped to None are deleted.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.translate, table, **kwargs)


	def sed(self, pattern:PatternLike, replacement:PatternLike = '', **kwargs):
		"""
		Substitutes all instances of a specified pattern with a replacement pattern.

		If no replacement pattern is provided, the matched pattern will be removed.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.

		Parameters:
			pattern: The pattern to search for in the lines of the Text object.
			replacement: The string to replace the matched pattern with. Defaults to an empty string.
			**kwargs: arguments to be passed to the re.sub operation

		Returns:
			A new Text object where the specified pattern has been replaced with the replacement pattern.
		"""

		return self.transform(re.sub, pattern, replacement, Placeholder, **kwargs, flatten=False)


	def tr(self, before:str, after:str, **kwargs):
		"""
		Translate each `before` character in the object into the corresponding `after` character.

		This function applies the built-in string method `translate()` to each line in the Text object,
		replacing all characters in the ``before`` string with the corresponding characters in the ``after`` string.

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.

		Parameters:
			before: A string containing the characters to be replaced.
			after: A string containing the replacement characters.
			start: Optional, the start point (index or pattern) to search for in the text.
			end: Optional, the end point (index or pattern) to search for in the text.

		Returns:
			A new Text object where all lines have been transformed according to the specified translation patterns.

		See str.translate and str.maketrans (https://docs.python.org/3/library/stdtypes.html#str.maketrans)
		for more information.
		"""

		table = str.maketrans(before, after)
		return self.transform(str.translate, table, **kwargs)

	# --- justify ---

	def center(self, width:int, fill:str = ' ', **kwargs):
		""" Returns a center-justified version of the text.
		Padding is done using the specified fill character (default is a space).

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.center, width, fill, **kwargs)

	def ljust(self, width:int, fill:str = ' ', **kwargs):
		""" Returns a left-justified version of the text.
		Padding is done using the specified fill character (default is a space).

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.ljust, width, fill, **kwargs)

	def rjust(self, width:int, fill:str = ' ', **kwargs):
		""" Returns a right-justified version of the string.
		Padding is done using the specified fill character (default is a space).

		If a 'start' or 'end' is provided, only the specified lines will be modified.
		See :py:meth:`Text.transform` for more information.
		"""
		return self.transform(str.rjust, width, fill, **kwargs)

	# --- change order ---

	def sort(self, key:Callable = None, reverse = False, unique = False, inplace = True):
		"""
		Sort the text in ascending order in-place.

		If a key function is given, apply it once to each line in the text and sort
		according to the return values of the function.

		The reverse flag can be set to sort in descending order.

		Parameters:
			key: A mapping function used to determine sort order.
			reverse: Sort the text in descending order.
			unique: Remove duplicate lines. Forces the method to return a new Text object.
				Default is False.
			inplace: If False, a new Text object containing the sorted lines is returned.
				Default is True.
		"""

		if inplace:
			if unique: self[:] = self.unique()
			return super().sort(key=key, reverse=reverse)
		else:
			return type(self)(sorted(self.unique() if unique else self), self.end)


	def reverse(self, inplace = True):
		"""
		Sort the text in ascending order in-place.

		If a key function is given, apply it once to each line in the text and sort
		according to the return values of the function.

		The reverse flag can be set to sort in descending order.

		Parameters:
			inplace: If False, a new Text object containing the sorted lines is returned.
				Default is True.
		"""

		if inplace:
			return super().reverse()
		else:
			return reversed(self)


	# === OUTPUT METHODS ===
	# methods for sending the content of the Text object.

	def print(self, file:Destination = None, mode:OpenMode = 'w') -> None:
		"""
		Prints the lines of the Text object to the specified file or IO stream.

		Keyword Arguments:
			file (Destination): The optional file or file-like object to which the message will be printed. If not provided, the message will only be printed to the standard output.
			mode (OpenMode): The mode in which the destination file will be opened. Defaults to 'w' (write).
		"""
		print(self, file=file, mode=mode, end=self.end)


	def tee(self, file:Destination = None, mode:OpenMode = 'w', stdout = True):
		"""
		Prints the lines of the Text object to the specified file or IO stream, and to stdout.

		Parameters:
			file: The optional file or file-like object to which the message will be printed. If not provided, the message will only be printed to the standard output.
			stdout: Determines if the tee() operation should print to sys.stdout
			mode (OpenMode): The mode in which the destination file will be opened. Defaults to 'w' (write).
		"""

		if file:   self.print(file=file, mode=mode)
		if stdout: self.print()
		return self


	# === SEARCH METHODS ===
	# methods for searching within the content of the Text object

	# noinspection PyRedeclaration
	def count(self, pattern:PatternLike = None, substring:str = None, start:SupportsIndex = None, end:SupportsIndex = None) -> int:
		"""
		Returns the number of times a specified value occurs in the text.

		Requires either a pattern or a substring to search for.
		If both values are provided, the pattern will be used.

		Parameters:
			pattern: Pattern to search for in the text.
			substring: Substring to search for in the text.
			start: Optional, indicates which line to start searching from.
			end: Optional, indicates the last line to include in the search space.

		Returns:
			The number of times the specified substring or pattern occurs in the text.

		Raises:
			TypeError: If neither a substring nor a pattern is provided as an argument.
		"""

		if pattern:
			return sum( len(re.findall(pattern, line)) for line in self[start:end] )
		elif substring:
			return sum( line.count(substring) for line in self[start:end] )
		else:
			raise TypeError("count() requires a pattern or substring argument")


	def find(self, pattern:PatternLike = None, substring:str = None, start:SupportsIndex = None, end:SupportsIndex = None, last = False) -> tuple[int,int]:
		"""
		Returns the position of the first occurence of a pattern or substring in the text.

		Requires either a pattern or a substring to search for.
		If both values are provided, the pattern will be used.

		The position is returned as a tuple in the form of `(line_index, string_index)`.

		Parameters:
			pattern: Pattern to search for in the text.
			substring: Substring to search for in the text.
			start: Optional, indicates which line to start searching from.
			end: Optional, indicates the last line to include in the search space.
			last: If true, searching starts at the end and works backward
				(end of last line for substrings, beginning of last line for patterns).

		Returns:
			(index, position): Tuple containing the index of the matching line,
				and the position of the match within that line.
				Returns None if no match is found.

		Raises:
			TypeError: If neither a substring nor a pattern is provided as an argument.
		"""

		if not (pattern or substring): raise TypeError("count() requires a pattern or substring argument")

		if last:
			lines = reversed(self)
			finder = 'rfind'
		else:
			lines = self
			finder = 'find'

		found = None
		for idx,line in enumerate(lines):
			if pattern:
				match = re.search(pattern, line)
				if match: found = match.start()
			elif substring:
				found = getattr(line, finder)(substring)

			if found and found != -1: return idx,found


	def rfind(self, substring:str = None, start:SupportsIndex = None, end:SupportsIndex = None) -> tuple[int,int]:
		"""
		Returns the position of the last occurence of a substring in the text.

		The position is returned as a tuple in the form of `(line_index, string_index)`.

		Parameters:
			substring: Substring to search for in the text.
			start: Optional, indicates which line to start searching from.
			end: Optional, indicates the last line to include in the search space.

		Returns:
			(index, position): Tuple containing the index of the matching line,
				and the position of the match within that line.

		Raises:
			TypeError: If neither a substring nor a pattern is provided as an argument.
		"""

		return self.find(None, substring, start, end, last=True)


	# === EVALUATION METHODS ===
	# methods for verifying the content of the Text object

	def endswith(self, suffix:Union[str,tuple[str, ...]], start:SupportsIndex = None, end:SupportsIndex = None) -> bool:
		"""
		Returns true if every line in the text ends with the specified value.

		Parameters:
			suffix: String(s) to check for at the end of each line. If multiple strings are provided, checks for any of them.
			start: Optional, indicates which line to start searching from.
			end: Optional, indicates the last line to include in the search space.
		"""

		return all( line.endswith(suffix, start, end) for line in self )


	def startswith(self, prefix:Union[str,tuple[str, ...]], start:SupportsIndex = None, end:SupportsIndex = None) -> bool:
		"""
		Returns true if every line in the text begins with the specified value.

		Parameters:
			prefix: String to check for at the start of each line.
			start: Optional, indicates which line to start searching from.
			end: Optional, indicates the last line to include in the search space.
		"""

		return all( line.startswith(prefix, start, end) for line in self )

	def contains(self, substring) -> bool:
		""" Returns True if the substring occurs anywhere in the text. """
		return any( substring in line for line in self )

	def isalnum(self) -> bool:
		""" Returns True if all characters in the text are alphanumeric. """
		return all( line.isalnum for line in self )

	def isalpha(self) -> bool:
		""" Returns True if all characters in the text are in the alphabet. """
		return all( line.isalpha for line in self )

	def isascii(self) -> bool:
		""" Returns True if all characters in the text are ascii characters. """
		return all( line.isascii() for line in self )

	def isdecimal(self) -> bool:
		""" Returns True if all characters in the text are decimals. """
		return all( line.isdecimal() for line in self )

	def isdigit(self) -> bool:
		""" Returns True if all characters in the text are digits. """
		return all( line.isdigit() for line in self )

	def islower(self) -> bool:
		""" Returns True if all characters in the text are lower case. """
		return all( line.islower() for line in self )

	def isnumeric(self) -> bool:
		""" Returns True if all characters in the text are numeric. """
		return all( line.isnumeric() for line in self )

	def isprintable(self) -> bool:
		""" Returns True if all characters in the text are printable. """
		return all( line.isprintable() for line in self )

	def isspace(self) -> bool:
		""" Returns True if all characters in the text are whitespaces. """
		return all( line.isspace() for line in self )

	def istitle(self) -> bool:
		""" Returns True if the text follows the rules of a title. """
		return all( line.istitle() for line in self )

	def isupper(self) -> bool:
		""" Returns True if all characters in the text are upper case. """
		return all( line.isupper() for line in self )




# === generic text-transformation functions ===

def dos2unix(infile:PathLike, outfile:PathLike = None):
	"""
	Mimics the dos2unix shell program.

	This function converts a text file from CRLF to LF line endings.

	Parameters:
		infile (os.PathLike[str]): The path to the input file.
		outfile (os.PathLike[str], optional): The path to the output file. If not provided, the same file as the input file will be used.

	Returns:
		None: The function does not return any value, but it modifies the input or output file.
	"""

	with open(infile, "rb") as file:
		## Convert example.txt from CRLF to LF
		buffer = file.read().replace(b'\r\n', b'\n')  # dos2unix "$dosfile"
	with open(outfile or infile, "wb") as file:
		file.write(buffer)


def upcase(text:StringList) -> Union[str,Text]:
	"""Convert the string(s) to upper-case."""
	return transform(text, str.upper)


def downcase(text:StringList) -> Union[str,Text]:
	"""Convert the string(s) to lower-case."""
	return transform(text, str.lower)


def transform(text:StringList, func:Callable, *args, **kwargs) -> Union[str,Text]:
	"""
	Applies a transformation function to a string, or to each item in a list.

	Parameters:
		text: the string or list of strings to be transformed.
		func: A callable function that will be applied to each line in the text.
		*args: Additional positional arguments to be passed to the specified function.
		**kwargs: Additional keyword arguments to be passed to the specified function.

	Returns:
		If text is a string, a transformed string will be returned.
		If text is a list of strings, a new :py:class:`Text` object will be returned,
		where all lines have been transformed according to the specified function and arguments.
	"""

	if isinstance(text, str):
		return text.__getattribute__(func.__name__)(*args, **kwargs)
	elif isinstance(text, Text):
		return text.transform(func, *args, **kwargs)
	elif isinstance(text, Sequence):
		return Text(text).transform(func, *args, **kwargs)
	else:
		raise TypeError(f"invalid type '{text.__class__}'")


# === Text() object generating functions ===

def cat(file:Destination) -> Text:
	"""
	Reads the contents of a file and returns a new Text object containing the lines of the file.

	Parameters:
		file: The file to read.

	Returns:
		A new :py:class:`Text` object containing the lines of the specified file.
	"""

	if isinstance(file, IO):
		return Text(file.readlines())
	else:
		return Text(file)


@overload
def grep(file:PathLike, pattern:PatternLike, **kwargs) -> Text: ...
@overload
def grep(pattern:PatternLike, **kwargs) -> Receiver: ...
def grep(pattern:PatternLike, file:PathLike = None, **kwargs) -> Union[Text, Receiver]:
	"""
	Searches for lines in a file that match a given pattern.

	Parameters:
		file: The file to search through.
		pattern: The pattern to search for in the text.
		**kwargs: keyword arguments not specified below will be passed to the :py:meth:`re.search` method

	Keyword Arguments:
		insensitive (bool): If True, the search will be case-insensitive.
		invert (bool): If True, the function will return lines that do *not* match the pattern.

	Returns:
		A new :py:class:`Text` object containing the lines that match the specified pattern.

		If no file is provided, a :py:class:`Receiver` is returned, for use in piped context
		(ex: ``cat('example.txt') | grep('substring')``)
	"""
	if file:
		return Text(file).grep(pattern, **kwargs)
	else:
		return Receiver(Text.grep, pattern, inplace=False, **kwargs)


@overload
def sed(pattern:PatternLike, replacement:PatternLike = '', file:PathLike = None, **kwargs) -> Text: ...
@overload
def sed(pattern:PatternLike, replacement:PatternLike = '', **kwargs) -> Receiver: ...
def sed(pattern:PatternLike, replacement:PatternLike = '', file:PathLike = None, **kwargs) -> Union[Text, Receiver]:
	"""
	Read in a file or :py:class:`Text`, substituting all instances of ``pattern`` with the pattern in ``replacement``.

	If a start or end is specified, only the matched lines will be modified.

	Parameters:
		file: The file to search through.
		pattern: The pattern to search for in the text.
		replacement: The string to replace the matched pattern with. If not provided, the matched pattern will be removed.
		**kwargs: keyword arguments not specified below will be passed to the :py:meth:`re.sub` method

	Keyword Arguments:
		start (LineIdentifier): Optional, the start point (index or pattern) to search for in the text.
		end (LineIdentifier): Optional, the end point (index or pattern) to search for in the text.
		invert (bool): If True, only lines that are *not* matched are returned.

	Returns:
		A new :py:class:`Text` object containing the lines where the specified pattern has been replaced with the replacement pattern.

		If no file is provided, a :py:class:`Receiver` is returned, for use in piped context
		(ex: ``cat('example.txt') | sed('substring', 'replacement')``)
	"""
	if file:
		return Text(file).sed(pattern, replacement, **kwargs)
	else:
		return Receiver(Text.sed, pattern, replacement, inplace=False, **kwargs)



@overload
def lines_between(start:PatternLike, end:PatternLike, file:PathLike, **kwargs) -> Text: ...
@overload
def lines_between(start:PatternLike, end:PatternLike, **kwargs) -> Receiver: ...
def lines_between(start:PatternLike, end:PatternLike, file:PathLike = None, **kwargs) -> Union[Text, Receiver]:
	"""
	Extracts lines between two patterns from a given file or :py:class:`Text`.

	Works similarly to the sed operation 'sed -n "/$start/,/$end/p" $file'

	Lines are returned starting with the line that matches the ``start`` pattern,
	continuously until (and including) the line that matches the ``end`` pattern.
	If the ``end`` pattern is never matched, then all remaining lines are matched.

	The ``start`` pattern may be matched multiple times. Each subsequent start-end block
	is appended to the returned lines.

	Parameters:
		file: The file to search through.
		start: The start pattern to search for in the text.
		end: The end pattern to search for in the text.
		**kwargs: keyword arguments not specified below will be passed to the :py:meth:`re.search` method

	Keyword Arguments:
		invert (bool): If True, only lines that are *not* matched are returned.

	Returns:
		A new :py:class:`Text` object containing all the lines between the specified start and end patterns.

		If no file is provided, a :py:class:`Receiver` is returned, for use in piped context
		(ex: ``cat('example.txt') | lines_between('start', 'end')``)
	"""
	if file:
		return Text(file).lines_between(start, end, **kwargs)
	else:
		return Receiver(Text.lines_between, start, end, **kwargs)

def upper() -> Receiver:
	""" Pipe Function. Convert the contents of a :py:class:`Text` object to upper-case. """
	return Receiver(Text.upper, inplace=False)

def lower() -> Receiver:
	""" Pipe Function. Convert the contents of a :py:class:`Text` object to lower-case. """
	return Receiver(Text.lower, inplace=False)

def head(length:int) -> Receiver:
	""" Pipe Function. Return the first N lines as a :py:class:`Text` object. """
	return Receiver(Text.__getitem__, slice(None, length))

def tail(length:int) -> Receiver:
	""" Pipe Function. Return the last N lines as a :py:class:`Text` object. """
	return Receiver(Text.__getitem__, slice(-length, None))

def tee(file:Destination, mode:OpenMode = 'w') -> Receiver:
	""" Pipe Function. Return the last N lines as a :py:class:`Text` object. """
	return Receiver(Text.tee, file=file, mode=mode)

def tr(before:str, after:str) -> Receiver:
	""" Pipe Function.
	Translate each `before` character in the object into the corresponding `after` character.

	This function applies the built-in string method `translate()` to each line in a :py:class:`Text` object,
	replacing all characters in the ``before`` string with the corresponding characters in the ``after`` string.

	Parameters:
		before: A string containing the characters to be replaced.
		after: A string containing the replacement characters.

	Returns:
		a :py:class:`Receiver` object, for use in pipe-chaining

	See str.translate and str.maketrans (https://docs.python.org/3/library/stdtypes.html#str.maketrans)
	for more information.
	"""
	return Receiver(Text.tr, before, after, inplace=False)