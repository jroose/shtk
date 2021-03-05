Streams
=======
shtk.Stream instances are pairs of file-like objects (one for reading data from
the process, one for writing data to the process) used for communication with
running processes.  If a stream is one way (e.g. FileStream) then the
underlying file-like objects reader or writer may be handles to os.devnull.

shtk.Stream instances are usually constructed internally within SHTK, rather
than being directly instantiated by the end user.

shtk.Stream
-----------

.. autoclass:: shtk.Stream
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

shtk.FileStream
---------------

.. autoclass:: shtk.FileStream
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

shtk.ManualStream
-----------------

.. autoclass:: shtk.ManualStream
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

shtk.NullStream
---------------

.. autoclass:: shtk.NullStream
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

shtk.PipeStream
---------------

.. autoclass:: shtk.PipeStream
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:
