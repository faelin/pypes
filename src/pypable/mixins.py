from __future__ import annotations

import os
import sys
import inspect
from typing import Any, Callable, Sequence, Union
from types import BuiltinFunctionType, FunctionType, LambdaType, MethodDescriptorType

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

class Placeholder:
	""" Throwaway class used to mark an intended variable injection into an :py:class:`Unpack` (*args or **kwargs). """
	pass


class UnpipableMixin:
	"""" Mixin class to handle unwanted/impossible piping ('|'). """
	def __or__(self, _): raise UnpipableError(self.__class__)


class Pipable:
	""" Mixin class to enable use of the pipe ('|') operator. """



	@staticmethod
	def _call_upon(__callable: Union[Callable, str], target, *args, **kwargs):
		""" Internal method used to resolve the contents of a Pipable or Receiver object in a pipe. """

		# search args/kwargs for Placeholder object and replace with `target`
		args = list(args)  # make args mutable
		placeholder_found = False
		for idx, arg in enumerate(args):
			if arg is Placeholder:
				args[idx] = target
				placeholder_found = True
		for key in kwargs:
			if kwargs[key] is Placeholder:
				kwargs[key] = target
				placeholder_found = True

		# if the callable is a function (not a method), then the args/kwargs must contain a Placeholder
		if not placeholder_found and isinstance(callable, (FunctionType, BuiltinFunctionType, LambdaType)):
			if args:
				raise TypeError('args must include a Placeholder object')
			else:
				# if args is empty, default to target as an argument
				args = (target,)

		# this has to be the first conditional, in case `target` is a subclass of `str`
		if isinstance(__callable, str):
			# if callable is a string, call as a method on `target`
			#   ex.   foo | ('print',)   ->   foo.print()
			result = getattr(target, __callable)(*args, **kwargs)

		elif isinstance(__callable, MethodDescriptorType) and issubclass(get_parent_class(__callable), target.__class__):
			# if callable is a method of `target`...
			#   ex.   Text() | grep('!')   ->   foo.grep('!')
			#         Text() | (Text.grep, '!')   ->   foo.grep('!')
			result = getattr(target, __callable.__name__)(*args, **kwargs)

		## For the moment, we have chosen to disable the namespace-collision resolution
		#
		# elif hasattr(target, __callable.__name__):
		## 	# if callable happens to collide with a method of `target`...
		## 	#   ex.   Text() | print('!)   ->   foo.print('!')
		## 	# this behavior should override built-ins, so it should come before the BuiltinFunctionType check
		# 	result = getattr(target, __callable.__name__)(*args, **kwargs)

		elif isinstance(__callable, BuiltinFunctionType):
			# if callable is a builtin function, call with `target` as an argument
			#   ex.   foo | len   ->   len(foo)
			result = __callable(target, *args, **kwargs)  # assume any args/kwargs were intended for the builtin
			if result is None: raise UnpipableError(result)

			# cast the result as a Receiver for piping.
			result = wrap_object(result, Receiver, invert_priority=True)

		elif __callable in functions_in_scope():
			# if callable is a defined function, try calling it with `target` and args
			result = __callable(target, *args, **kwargs)

		elif isinstance(__callable, type):
			# if callable is a class, attempt to extend it using the Receiver mixin
			receivable_class = extend_class(Receiver, __callable)  # Receiver comes first to make sure that magic methods are correctly overridden
			# then we cast `target` as the new class
			result = receivable_class(target, *args, **kwargs)  # assume any args/kwargs were intended for the constructor

		else:
			# if all else fails, we attempt to cast `target` as
			# whatever the parent class of the __callable is,
			# and then make the call against the new object
			cast = get_parent_class(__callable)
			if isinstance(cast, type) and not isinstance(target, cast):
				target = cast(target)
				result = getattr(target, __callable.__name__)(*args, **kwargs)
			else:
				result = __callable(target, *args, **kwargs)

		return result


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
		result = type(self)._call_upon(__callable, self, *args, **kwargs)

		# follow chain
		if chain: result = result | chain

		return result


# noinspection PyInitNewSignature
class Receiver(Pipable):
	""" Receivers are a special class intended to go on the right side of a pipe ('|') operation.

	Receivers are callable, and when called they resolve to their `callable` property.
	Any args or kwargs provided when the Receiver is instantiated are added to args/kwargs provided
	when resolving the callable.

	Parameters:
		__callable: The callable function or method to be executed with the right-hand value.
		*args: Additional positional arguments to be passed to the `__callable` function.
		**kwargs: Additional keyword arguments to be passed to the `__callable` function.

	Attributes:
		callable (Union[Callable, str]): The callable function or method to be executed with the right-hand value.
		args (tuple): Additional positional arguments to be passed to the `callable` function.
		kwargs (dict): Additional keyword arguments to be passed to the `callable` function.
		chain (Receiver | None): The next receiver in the pipe chain.
	"""

	def __init__(self, __callable:Union[Callable,str], *args, **kwargs):
		self.callable = __callable
		self.args = args
		self.kwargs = kwargs
		self.chain = None


	def __call__(self, value, *args, **kwargs):
		# make the call with the left-hand argument of the pipe as the target
		return type(self)._call_upon(self.callable, value, *self.args, *args, **self.kwargs, **kwargs)


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

		result = self(lhs)

		# finalize return
		if self.chain:
			return result | self.chain
		else:
			return result
