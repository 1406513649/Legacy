
from .sampling import SamplingMethod

def Method(method, id_method, model_pointer, **kwargs):
    if method.lower() == 'sampling':
        return SamplingMethod(id_method, model_pointer, **kwargs)
    raise ValueError(method)
