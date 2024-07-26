import os
import sys
from typing import get_args, get_origin
from typing import Literal, Union, Sequence, Mapping, Callable, IO
import re
import inspect


# === PUBLIC TYPES ===

IntLike = Union[int, str]

PathLike = Union[str, os.PathLike]

Destination = Union[IO, PathLike]

PatternLike = Union[str, re.Pattern]

LineIdentifier = Union[int, PatternLike]

RegexFlag = Union[int, re.RegexFlag]

YesNo = Literal['y','n', True, False]

StringList = Union[str, Sequence[str]]

Receiver = tuple[Callable, Sequence, Mapping]



_OpenDirection = Literal['r', 'w', 'x', 'a']
_OpenEncoding = Literal['b', 't']
_OpenModifier = Literal['+', '']
# noinspection PyTypeHints
OpenMode = Literal[
					tuple(
							[x + z for x in get_args(_OpenDirection) for z in get_args(_OpenModifier)]
							+
							[x + y + z for x in get_args(_OpenDirection) for y in get_args(_OpenEncoding) for z in get_args(_OpenModifier)]
						 )
				  ]

class Placeholder:
	""" Throwaway class used to mark an intended variable injection into an :py:class:`Unpack` (*args or **kwargs). """
	pass


# === TYPING HELPERS ===

def get_parent_class(__obj):
	""" Return the parent class of an object or function. """
	if hasattr(__obj, '__module__') and __obj.__module__ is not None:
		module = sys.modules[__obj.__module__]
		class_name = __obj.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
		return getattr(module, class_name)
	elif hasattr(__obj, '__qualname__') and __obj.__qualname__ is not None:
		module = sys.modules['builtins']
		class_name = __obj.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
		return getattr(module, class_name)
	else:
		return __obj.__class__


def extend_class(cls:type, *mixins:type, **attrs) -> type:
	""" Shorthand method to extend an object of unknown type using a mixin. """

	if issubclass(cls, mixins): return cls  # return if already extended

	mixin_names = [ mixin.__name__.title() for mixin in mixins ]
	extension_name = ''.join(mixin_names) + cls.__name__.title()
	classes_in_frame = { name: obj for name, obj in inspect.getmembers(sys.modules[__name__]) if inspect.isclass(obj) }

	# generate the extension
	if extension_name in classes_in_frame:
		# the extended class already exists, attempt to instantiate it with cls
		return classes_in_frame[extension_name]
	else:
		# otherwise we create the extended class, then attempt to instantiate it with cls
		extended_class = type(extension_name, (*mixins, cls), attrs)
		return extended_class


def is_str_list(val):
	""" Determines whether all objects in the list are strings """
	if val is str:
		return False
	else:
		return all(isinstance(x, str) or hasattr(x, '__str__') for x in val)


def is_subscripted_type(obj, typ):
	""" Like isinstance(), but allows subscripted types. """
	if get_origin(typ) is None:
		return isinstance(obj, typ)
	elif get_origin(typ) is Union:
		return any(isinstance(obj, _type) for _type in get_args(typ))
	else:
		return isinstance(obj, get_origin(typ)) and all(isinstance(arg, typ_arg) for arg, typ_arg in zip(obj, get_args(typ)))


def class_path(__obj):
	cls = __obj.__class__

	if hasattr(cls, '__module__'):
		module = cls.__module__
		if module not in ('builtins', '__builtin__', '__main__'):
			return module + '.' + cls.__name__

	return cls.__name__ # avoid outputs like '__builtin__.str'