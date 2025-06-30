import logging
from typing import Final

from fltk.fegen import bootstrap, gsm2tree
from fltk.iir.context import create_default_context
from fltk.iir.py import reg as pyreg

LOG: Final = logging.getLogger(__name__)


def test_gsm2model() -> None:
    context = create_default_context()
    cst = gsm2tree.CstGenerator(grammar=bootstrap.grammar, py_module=pyreg.Builtins, context=context)
    for rule in cst.grammar.rules:
        model = cst.model_for_rule(rule, [])
        LOG.info("%s: %s", rule.name, model)
