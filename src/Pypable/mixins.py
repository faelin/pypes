import os
import sys
import inspect
from typing import IO, Any, Callable, Sequence, Union
from types import BuiltinFunctionType

from Pypable.typing import get_parent_class, extend_class, isinstance
from Pypable.typing import PathLike, Destination
from Pypable.printers import print

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


class PipableMixin:
	""" Mixin class to enable use of the pipe ('|') operator. """

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
	def __or__(self, receiver):
		"""
		Overrides the '|' operator to enable left-associative piping of return values.

		This is equivalent to the POSIX pipe operation chaining.
		In a shell script, this might looks like ``cat 'example.txt' | grep 'some text'``.

		If a

		Parameters:
			receiver (Receiver, Callable): the object to receive the value of the left-hand object.

		Returns:
			The result of the right-hand callable.

		Examples:
			>>> from Pypable.text import cat, grep, sed
			>>> cat('example.txt') | grep('some text') | sed('_', '.')
		"""

		# set defaults
		args = ()
		kwargs = {}
		chain = None


		# extract arguments
		if isinstance(receiver, Receiver):
			__callable = receiver.__callable
			args = receiver.__args
			kwargs = receiver.__kwargs
			chain = receiver.chain

		elif isinstance(receiver, str) or receiver is None:
			# prevent a plain string from being interpreted as a list of arguments
			raise TypeError(f"cannot pipe to object of type '{receiver.__class__.__name__}'")

		elif isinstance(receiver, Sequence):
			__callable = receiver[0]
			args = receiver[1:]
			kwargs = {}

			if len(args):
				if isinstance(args[-1], dict):
					kwargs = args[-1]  # copy dict from __args to kwargs
					args = args[:-1]  # pop dict from __args

				if len(args) == 1:
					args = args[0]  # if only one item is left, it's an *args tuple

		else:
			__callable = receiver


		# process call
		if get_parent_class(__callable) == self.__class__:
			# if right-hand is same class as left-hand, call as a method of left-hand object
			#   ex.   Text() | grep('!)   ->   foo.grep('!')
			#         Text() | (Text.grep, '!')   ->   foo.grep('!')
			result = getattr(self, __callable.__name__)(*args, **kwargs)

		# this has to be the second conditional, in case `self` is a subclass of `str`
		elif isinstance(__callable, str):
			# if right-hand is a string, call as a method of left-hand object
			#   ex.   foo | ('print',)   ->   foo.print()
			result = getattr(self, __callable)(*args, **kwargs)

		elif hasattr(self, __callable.__name__):
			# if right-hand is a callable that exists as a method of the left-hand object...
			#   ex.   Text() | print('!)   ->   foo.print('!')
			# this behavior should override built-ins, so it should come before the BuiltinFunctionType check
			result = getattr(self, __callable.__name__)(*args, **kwargs)

		elif isinstance(__callable, BuiltinFunctionType):
			# if right-hand is a builtin function, call left-hand as an argument
			#   ex.   foo | len   ->   len(foo)
			result = __callable(self, *args, **kwargs)  # assume any args/kwargs were intended for the builtin
			if result is None: raise UnpipableError(result)

			pipable_obj = extend_class(result.__class__, Receiver)
			result = pipable_obj(result)

		elif __callable in functions_in_scope():
			# if right-hand is a defined function, try calling it with self and args
			result = __callable(self, *args, **kwargs)
			pipable_obj = extend_class(result.__class__, Receiver)
			result = pipable_obj(result)

		elif isinstance(__callable, type):
			# if right-hand is a class, attempt to extend it using the PipableMixin mixin
			pipable_obj = extend_class(__callable, Receiver)
			result = pipable_obj(self, *args, **kwargs)  # assume any args/kwargs were intended for the constructor

		else:
			# if all else fails, we attempt to cast `self` as
			# whatever the parent class of the __callable is,
			# and then make the call against the new object
			cast = get_parent_class(__callable)(self)
			result = getattr(cast, __callable.__name__)(*args, **kwargs)


		# finalize return
		if chain:
			return result | chain
		else:
			return result


# noinspection PyInitNewSignature
class Receiver(PipableMixin):
	""" Receivers are a special class intended to go on the right side of a pipe ('|') operation. """

	def __init__(self, __callable:Union[Callable,str], *args, **kwargs):
		self.__callable = __callable
		self.__args = args
		self.__kwargs = kwargs
		self.chain = None

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