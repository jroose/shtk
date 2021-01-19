from .PipelineNodeFactory import PipelineOrFactory

def or_(first_child, *other_children):
    return PipelineOrFactory(first_child, *other_children)
