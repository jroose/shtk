Pipeline Nodes
==============
shtk.PipelineNodeFactory subclasses are templates used to define the properties
of shtk.PipelineNode instances.  shtk.PipelineNode instances are nodes within a
directed acyclic graph (DAG) that represent a process pipeline.  

The leaf nodes of this DAG are always PipelineProcess instances representing an
individual process that is part of the pipeline.  

PipelineNode instances can be used to communicate, start, and stop individual
processes within a process pipeline.

shtk.PipelineNode
-----------------

.. autoclass:: shtk.PipelineNode
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

shtk.PipelineChannel
--------------------

.. autoclass:: shtk.PipelineChannel
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

shtk.PipelineProcess
--------------------

.. autoclass:: shtk.PipelineProcess
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:

