"""Unit tests for CompilerContext and TypeRegistry."""

import pytest

from fltk.fegen import bootstrap, gsm2parser, gsm2tree
from fltk.iir import model as iir
from fltk.iir.context import CompilerContext, TypeRegistry, create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg


class TestTypeRegistry:
    """Test TypeRegistry functionality."""

    def test_empty_registry(self):
        """Test that empty registry behaves correctly."""
        registry = TypeRegistry()

        with pytest.raises(KeyError):
            registry.lookup(iir.String)

        assert not registry.contains(iir.String)

    def test_register_and_lookup(self):
        """Test basic register and lookup operations."""
        registry = TypeRegistry()
        type_info = pyreg.TypeInfo(typ=iir.String, module=pyreg.Builtins, name="str")

        registry.register_type(type_info)

        assert registry.contains(iir.String)
        retrieved = registry.lookup(iir.String)
        assert retrieved == type_info

    def test_identical_reregistration(self):
        """Test that registering identical types is allowed."""
        registry = TypeRegistry()
        type_info = pyreg.TypeInfo(typ=iir.String, module=pyreg.Builtins, name="str")

        # Register once
        registry.register_type(type_info)

        # Register again with identical info - should not raise
        registry.register_type(type_info)

        # Should still work correctly
        assert registry.lookup(iir.String) == type_info

    def test_conflicting_registration(self):
        """Test that conflicting registrations are rejected."""
        registry = TypeRegistry()

        # Register with one module
        type_info1 = pyreg.TypeInfo(typ=iir.String, module=pyreg.Builtins, name="str")
        registry.register_type(type_info1)

        # Try to register with different module
        type_info2 = pyreg.TypeInfo(typ=iir.String, module=pyreg.Module(("different",)), name="str")

        with pytest.raises(ValueError, match="Conflicting type registration"):
            registry.register_type(type_info2)

    def test_copy_registry(self):
        """Test that registry copy works correctly."""
        registry = TypeRegistry()
        type_info = pyreg.TypeInfo(typ=iir.String, module=pyreg.Builtins, name="str")
        registry.register_type(type_info)

        # Copy the registry
        copied = registry.copy()

        # Both should have the type
        assert registry.lookup(iir.String) == type_info
        assert copied.lookup(iir.String) == type_info

        # Register in original - should not affect copy
        type_info2 = pyreg.TypeInfo(typ=iir.Bool, module=pyreg.Builtins, name="bool")
        registry.register_type(type_info2)

        assert registry.contains(iir.Bool)
        assert not copied.contains(iir.Bool)


class TestCompilerContext:
    """Test CompilerContext functionality."""

    def test_default_initialization(self):
        """Test that CompilerContext initializes correctly."""
        context = CompilerContext()

        # Should auto-create python_type_registry
        assert context.python_type_registry is not None
        assert isinstance(context.python_type_registry, TypeRegistry)

    def test_explicit_registry(self):
        """Test CompilerContext with explicit registry."""
        registry = TypeRegistry()
        context = CompilerContext(python_type_registry=registry)

        assert context.python_type_registry is registry

    def test_create_default_context(self):
        """Test that create_default_context creates usable context."""
        context = create_default_context()

        assert context.python_type_registry is not None

        # Should have built-in types registered
        assert context.python_type_registry.contains(iir.String)
        assert context.python_type_registry.contains(iir.Bool)
        assert context.python_type_registry.contains(iir.IndexInt)

    def test_multiple_contexts_isolated(self):
        """Test that multiple contexts are isolated from each other."""
        context1 = create_default_context()
        context2 = create_default_context()

        # Both should have built-ins
        assert context1.python_type_registry.contains(iir.String)
        assert context2.python_type_registry.contains(iir.String)

        # Register a custom type in context1 only
        custom_type = iir.Type.make(cname="CustomType")
        type_info = pyreg.TypeInfo(typ=custom_type, module=pyreg.Builtins, name="CustomType")
        context1.python_type_registry.register_type(type_info)

        # Should be in context1 but not context2
        assert context1.python_type_registry.contains(custom_type)
        assert not context2.python_type_registry.contains(custom_type)


class TestIntegration:
    """Integration tests with actual parser components."""

    def test_multiple_parser_generators(self):
        """Test that multiple ParserGenerator instances work with isolated contexts."""
        # Create two isolated contexts
        context1 = create_default_context()
        context2 = create_default_context()

        # Create two parser generators with the same grammar but different contexts
        cst_module = pyreg.Module(("test", "module"))

        # Add trivia rules to grammar
        enhanced_grammar1 = gsm2parser.gsm.add_trivia_rule_to_grammar(bootstrap.grammar, context1)
        enhanced_grammar2 = gsm2parser.gsm.add_trivia_rule_to_grammar(bootstrap.grammar, context2)

        cstgen1 = gsm2tree.CstGenerator(grammar=enhanced_grammar1, py_module=cst_module, context=context1)
        pgen1 = gsm2parser.ParserGenerator(grammar=enhanced_grammar1, cstgen=cstgen1, context=context1)

        cstgen2 = gsm2tree.CstGenerator(grammar=enhanced_grammar2, py_module=cst_module, context=context2)
        pgen2 = gsm2parser.ParserGenerator(grammar=enhanced_grammar2, cstgen=cstgen2, context=context2)

        # Both should work without conflicts
        assert pgen1.parser_class is not None
        assert pgen2.parser_class is not None

        # They should be different instances
        assert pgen1 is not pgen2
        assert pgen1.context is not pgen2.context
        assert cstgen1.context is not cstgen2.context

    def test_context_type_annotations(self):
        """Test that context-aware type annotation functions work."""
        context1 = create_default_context()
        context2 = create_default_context()

        # Should produce same results for built-in types
        str_annotation1 = compiler.iir_type_to_py_annotation(iir.String, context1)
        str_annotation2 = compiler.iir_type_to_py_annotation(iir.String, context2)
        assert str_annotation1 == str_annotation2 == "str"

    def test_isolated_context_prevents_conflicts(self):
        """Test that isolated contexts prevent the conflicts that global registry causes."""
        # Create two contexts with different module names for the same grammar
        context1 = create_default_context()
        context2 = create_default_context()

        # Both try to register the same grammar types but with different modules
        cst_module1 = pyreg.Module(("project1", "parser"))
        cst_module2 = pyreg.Module(("project2", "parser"))

        # This should work without conflicts because each uses isolated contexts
        # Add trivia rules to grammar
        enhanced_grammar1 = gsm2parser.gsm.add_trivia_rule_to_grammar(bootstrap.grammar, context1)
        enhanced_grammar2 = gsm2parser.gsm.add_trivia_rule_to_grammar(bootstrap.grammar, context2)

        cstgen1 = gsm2tree.CstGenerator(grammar=enhanced_grammar1, py_module=cst_module1, context=context1)
        pgen1 = gsm2parser.ParserGenerator(grammar=enhanced_grammar1, cstgen=cstgen1, context=context1)

        cstgen2 = gsm2tree.CstGenerator(grammar=enhanced_grammar2, py_module=cst_module2, context=context2)
        pgen2 = gsm2parser.ParserGenerator(grammar=enhanced_grammar2, cstgen=cstgen2, context=context2)

        # Both should succeed without conflicts
        assert pgen1.parser_class is not None
        assert pgen2.parser_class is not None

        # Verify they use different contexts
        assert pgen1.context is context1
        assert pgen2.context is context2
        assert context1 is not context2
