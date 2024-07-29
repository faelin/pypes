from __future__ import annotations

import os
import sys
import inspect
from typing import Any, Callable, Sequence, Union
from types import BuiltinFunctionType, MethodDescriptorType

from pypable.typing import get_parent_class, extend_class, wrap_object, isinstance
from pypable.typing import PathLike, Destination, ReceiverLike
from pypable.printers import print

# === HELPER FUNCTIONS ===

def functions_in_scope(module = None):
	return [obj for name,obj in inspect.getmembers(sys.modules[module or __name__]) if inspect.isfunction(obj)]


# === EXCEPTIONS ===

class PipeError(TypeError):
	""" Exception raised an error has occurred during a pipe operation. """
	__module__ = Exception.__module__

class UnpipableError(PipeError):
	""" Exception raised when an attempt is made to pipe an object that cannot be piped. """
	__module__ = Exception.__module__

	def __init__(self, __obj:Any = '', *args):
		"""
		Parameters:
			__obj: Optional, the unpipable object that caused the exception.
			*args: additional information for the exception
		"""

		message = "cannot pipe object of type '{}'"
		if __obj == '':
			out = args
		if isinstance(__obj, str):
			out = (__obj, *args)
		elif isinstance(__obj, type):
			out = (message.format(__obj.__name__), *args)
		else:
			out = (message.format(__obj.__class__.__name__), *args)

		super().__init__(*out)


# === MIXINS ===

class UnpipableMixin:
	"""" Mixin class to handle unwanted/impossible piping ('|'). """
	def __or__(self, _): raise UnpipableError(self.__class__)


class Pipable:
	""" Mixin class to enable use of the pipe ('|') operator. """

	@staticmethod
	def _call_upon(__callable:Union[Callable,str], other, *args, **kwargs):
		""" Internal method used to resolve the contents of a Pipable or Receiver object in a pipe. """

		# this has to be the first conditional, in case `other` is a subclass of `str`
		if isinstance(__callable, str):
			# if callable is a string, call as a method on `other`
			#   ex.   foo | ('print',)   ->   foo.print()
			result = getattr(other, __callable)(*args, **kwargs)

		elif isinstance(__callable, MethodDescriptorType) and issubclass(get_parent_class(__callable), other.__class__):
			# if callable is a method of `other`...
			#   ex.   Text() | grep('!')   ->   foo.grep('!')
			#         Text() | (Text.grep, '!')   ->   foo.grep('!')
			result = getattr(other, __callable.__name__)(*args, **kwargs)

		## For the moment, we have chosen to disable the namespace-collision resolution
		#
		# elif hasattr(other, __callable.__name__):
		## 	# if callable happens to collide with a method of `other`...
		## 	#   ex.   Text() | print('!)   ->   foo.print('!')
		## 	# this behavior should override built-ins, so it should come before the BuiltinFunctionType check
		# 	result = getattr(other, __callable.__name__)(*args, **kwargs)

		elif isinstance(__callable, BuiltinFunctionType):
			# if callable is a builtin function, call with `other` as an argument
			#   ex.   foo | len   ->   len(foo)
			result = __callable(other, *args, **kwargs)  # assume any args/kwargs were intended for the builtin
			if result is None: raise UnpipableError(result)

			# cast the result as a Receiver for piping.
			result = wrap_object(result, Receiver)

		elif __callable in functions_in_scope():
			# if callable is a defined function, try calling it with `other` and args
			result = __callable(other, *args, **kwargs)

		elif isinstance(__callable, type):
			# if callable is a class, attempt to extend it using the Receiver mixin
			receivable_class = extend_class(__callable, Receiver)
			# then we cast `other` as the new class
			result = receivable_class(other, *args, **kwargs)  # assume any args/kwargs were intended for the constructor

		else:
			# if all else fails, we attempt to cast `other` as
			# whatever the parent class of the __callable is,
			# and then make the call against the new object
			cls = get_parent_class(__callable)
			if isinstance(cls, type):
				other = wrap_object(other, cls)
				result = getattr(other, __callable.__name__)(*args, **kwargs)
			else:
				result = __callable(other, *args, **kwargs)


		# wrap object for piping if it is not already wrapped
		if issubclass(result.__class__, Pipable):
			return result
		else:
			# cast as Receiver because __call_upon resolution could occur on either side of a pipe
			receiver = wrap_object(result, Receiver)
			receiver.value = result
			return receiver


	def __lt__(self, other): return NotImplemented
	def __lshift__(self, other): return NotImplemented

	def __gt__(self, file:Destination):
		""" Attempts to (over)write the left-hand value to the file or file-path on the right. """
		if isinstance(file, Destination):
			return print(self, file=file, mode='w')
		else:
			return NotImplemented

	def __rshift__(self, file:Destination):
		""" Attempts to append the left-hand value to the file or file-path on the right. """
		if isinstance(file, Destination):
			if isinstance(self, Receiver):
				self.chain = Receiver(print, file=file, mode='a')
				return None
			else:
				return print(self, file=file, mode='a')
		else:
			return NotImplemented

	# noinspection PyUnresolvedReferences
	def __or__(self, rhs:Union[Receiver, ReceiverLike, str, BuiltinFunctionType, type]):
		"""
		Overrides the bitwise-OR operator ('|') to enable left-associative piping of values.
		::

		->	Pipable(lhs) | Receiver(rhs, *args)   # lhs.rhs(*args)
		->	Pipable(lhs) | (rhs, *args)           # lhs.rhs(*args)

		|

		This is equivalent to POSIX pipe operation chaining.
		In a shell script, this might looks like:
		::
			cat 'example.txt' | grep 'some text'

		|

		Parameters:
			rhs: the object to receive the value of the left-hand object.

		Returns:
			The result of the right-hand callable.

		Examples:
			>>> from pypable.text import cat, grep, sed
			>>> cat('example.txt') | grep('some text') | sed('_', '.')
		"""

		if isinstance(rhs, str) or rhs is None:
			# prevent a plain string from being interpreted as a list of arguments
			raise TypeError(f"cannot pipe to object of type '{rhs.__class__.__name__}'")

		# set defaults
		args, kwargs = (), {}
		chain = None

		# extract arguments
		if isinstance(rhs, Receiver):
			__callable = rhs.__callable
			args = rhs.__args
			kwargs = rhs.__kwargs
			chain = rhs.chain

		elif isinstance(rhs, Sequence):
			__callable = rhs[0]
			args = rhs[1:]

			if len(args):
				if isinstance(args[-1], dict):
					kwargs = args[-1]  # copy dict from __args to kwargs
					args = args[:-1]  # pop dict from __args

				if len(args) == 1:
					args = args[0]  # if only one item is left, it's an *args tuple

		else:
			__callable = rhs


		# make the call with `self` as the target
		result:Pipable = type(self)._call_upon(__callable, self, *args, **kwargs)

		# follow chain
		if chain: result = result | chain

		return result


# noinspection PyInitNewSignature
class Receiver(Pipable):
	""" Receivers are a special class intended to go on the right side of a pipe ('|') operation. """

	def __init__(self, __callable:Union[Callable,str], *args, value = None, **kwargs):
		self.__callable = __callable
		self.__args = args
		self.__kwargs = kwargs
		self.chain = None
		self.value = value

	def __lt__(self, other): return NotImplemented
	def __gt__(self, other): return NotImplemented

	def __lshift__(self, path:PathLike):
		""" Feeds the right-hand value to the '<<' (:py:meth:`__lshift__`) operator of the object on the left. """

		if isinstance(path, str) or isinstance(path, os.PathLike):
			self.chain = Receiver('__lshift__', path)
			return self
		else:
			return NotImplemented

	def __rshift__(self, out:Destination):
		""" Feeds the right-hand value to the '>>' (:py:meth:`__rshift__`) operator of the object on the left. """
		if isinstance(out, Destination):
			self.chain = Receiver('__rshift__', out)
			return self
		else:
			return NotImplemented

	def __ror__(self, lhs):
		"""
		Overrides the bitwise-OR operator ('|') to enable left-associative piping of values.

		This method is used as a fallback when the left-hand side (lhs) is not a Pipable object.
		::

		->	lhs | Receiver(rhs, *args)   # rhs(lhs, *args
		->	lhs | (rhs, *args)           # rhs(lhs, *args)

		|

		This is equivalent to the POSIX pipe operation chaining.
		In a shell script, this might looks like:
		::
			cat 'example.txt' | grep 'some text'

		|

		Parameters:
			lhs: the object to receive the value of the left-hand object.

		Returns:
			The result of the right-hand callable.

		Examples:
			>>> from pypable.text import cat, grep, sed
			>>> cat('example.txt') | grep('some text') | sed('_', '.')
		"""

		__callable = self.__callable
		args = self.__args
		kwargs = self.__kwargs
		chain = self.chain

		# make the call with the left-hand argument of the pipe as the target
		result:Receiver = type(self)._call_upon(__callable, lhs, *args, **kwargs)

		# finalize return
		if chain:
			return result | chain
		else:
			return result.value