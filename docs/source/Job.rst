Jobs
====

Jobs represent and control running pipelines.  They are returned by
shtk.Shell.run() and used by other internal methods of shtk.Shell, such as
shtk.Shell.evaluate().  Provided functionality includes starting, killing, and
awaiting completion of process pipelines.  

The Job.run() method is also responsible for instantiating
shtk.PipelineNodeFactory templates to create shtk.PipelineNode instances, as
well as instantiating StreamFactory templates to create shtk.Stream instances.

shtk.Job
--------

.. autoclass:: shtk.Job
	:members:
	:undoc-members:
	:show-inheritance:
	:inherited-members:
