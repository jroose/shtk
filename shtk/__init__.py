"""
SHTK is a package of resources for running, managing, and communicating with
subprocess commands.
"""

from .Job import *
from .PipelineNode import *
from .PipelineNodeFactory import *
from .Shell import *
from .Stream import *
from .StreamFactory import *

from . import _version
__version__ = _version.get_versions()['version']
