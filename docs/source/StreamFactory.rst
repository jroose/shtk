Stream Factories
================
shtk.StreamFactory subclasses are templates used to define the properties of
shtk.Stream instances.  shtk.Stream instances are pairs of file-like objects
(one for reading data from the process, one for writing data to the process)
used for communication with running processes.  

shtk.StreamFactory instances are typically constructed via calls to
shtk.PipelineNodeFactory.stdin(), shtk.PipelineNodeFactory.stdout(), and
shtk.PipelineNodeFactory.stderr().

shtk.StreamFactory
------------------

.. autoclass:: shtk.StreamFactory
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

shtk.FileStreamFactory
----------------------

.. autoclass:: shtk.FileStreamFactory
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

shtk.ManualStreamFactory
------------------------

.. autoclass:: shtk.ManualStreamFactory
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

shtk.NullStreamFactory
----------------------

.. autoclass:: shtk.NullStreamFactory
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

shtk.PipeStreamFactory
----------------------

.. autoclass:: shtk.PipeStreamFactory
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

