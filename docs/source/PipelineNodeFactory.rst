Pipeline Node Factories
=======================
shtk.PipelineNodeFactory subclasses are templates used to define the properties
of shtk.PipelineNode instances.  shtk.PipelineNode instances are nodes within a
directed acyclic graph (DAG) that represent a process pipeline.  

shtk.PipelineNodeFactory instances are useful because they enable (1) running
process pipelines multiple times (2) displaying the commands that will be run
as part of the pipeline prior to executing the command and (3) composing
partial pipelines into more complex process pipelines.

PipelineNodeFactory instances are usually constructed by a
shtk.Shell.command(), or by using the pipe operator to connect multiple
PipelineProcessFactory instances together into a single process pipeline.

shtk.PipelineNodeFactory
------------------------

.. autoclass:: shtk.PipelineNodeFactory
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

shtk.PipelineChannelFactory
---------------------------

.. autoclass:: shtk.PipelineChannelFactory
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

shtk.PipelineProcessFactory
---------------------------

.. autoclass:: shtk.PipelineProcessFactory
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

