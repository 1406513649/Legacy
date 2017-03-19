import sys

from src.base.errors import WasatchError, UserInputError
from src.fem.materials.elastic import Elastic
from src.fem.materials.viscoplastic import ViscoPlastic

models = {"VISCOPLASTIC": ViscoPlastic,
          "ELASTIC": Elastic}


def create_material(matname):
    model = models.get(matname.upper())
    if model is None:
        raise UserInputError("model {0} not recognized".format(matname))
    return model()
