import os
import subprocess

from ICPSR.utilities.typing import PathLike


PATH = '/usr/bin:/bin:/opt/hermes/bin:/opt/icpsr/bin:/opt/icpsr/lib/shlib:/opt/varmet/bin:/opt/SPSS/bin:/opt/python/bin:/opt/sda/bin:/opt/jq/bin'
os.environ['PATH'] = PATH


def run(program:str, *args, check:bool = True, env:dict[str,str] = None, path:PathLike = None) -> str:
	"""
	Thin wrapper around `subprocess.run()` with some default args.

	Args:
		program: Name of the program to be invoked (path to the program is optional).
		*args: Arguments to send to the program.
		check: Throw an error if the subprocess exits with a non-zero exit status. Defaults to True.
		env: Optional, a dictionary to use as environment variable values for the subprocess.
		path: Optional, the PATH environment variable to launch the subprocess with.
			Overrides any PATH included in ``env``.

	Returns:
		The STDOUT that results from the executed command.

	Raises:
		subprocess.CalledProcessError
	"""

	if path is None: path = PATH
	if env is None: env = {}
	env.update({'PATH': path})

	return subprocess.run((program, *args), capture_output=True, text=True, env=env, check=check).stdout