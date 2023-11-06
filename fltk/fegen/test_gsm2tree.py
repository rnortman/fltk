import logging
from typing import Final

from fltk.fegen import bootstrap, gsm2tree
from fltk.iir.py import reg as pyreg

LOG: Final = logging.getLogger(__name__)


def test_gsm2model() -> None:
    cst = gsm2tree.CstGenerator(grammar=bootstrap.grammar, py_module=pyreg.Builtins)
    for rule in cst.grammar.rules:
        model = cst.model_for_rule(rule, [])
        LOG.info("%s: %s", rule.name, model)
