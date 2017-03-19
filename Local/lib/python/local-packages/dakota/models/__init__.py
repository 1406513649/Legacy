
__all__ = ['Model']

from ._model import Model as DM

def Model(id_model, variables_pointer, responses_pointer,
        hierarchical_tagging=None):

    return DM(id_model, variables_pointer, responses_pointer,
              hierarchical_tagging=hierarchical_tagging)
