import typing

import enforce.nodes as nodes
from .validators import Validator
from .utils import visit


class Parser:

    def __init__(self):
        self.validator = Validator()
        self._mapping = {
            typing.UnionMeta: self._parse_union,
            typing.TypeVar: self._parse_type_var,
            typing.TupleMeta: self._parse_tuple
            }
    
    def parse(self, hint, hint_name):
        self.globals = {}
        parsers = self._map_parser(None, hint, self)
        tree = visit(parsers)
        self.validator.roots[hint_name] = tree

    def _map_parser(self, node, hint, caller):
        parser = self._mapping.get(type(hint), self._parse_default)
        yield parser(node, hint, caller)

    def _parse_default(self, node, hint, parser):
        new_node = yield nodes.SimpleNode(hint)
        parser.validator.all_nodes.append(new_node)
        yield self._yield_parsing_result(node, new_node)

    def _parse_union(self, node, hint, parser):
        """
        Parses Union type
        Union type has to be parsed into multiple nodes 
        in order to enable further validation of nested types
        """
        new_node = yield nodes.UnionNode()
        parser.validator.all_nodes.append(new_node)
        for element in hint.__union_params__:
            yield self._map_parser(new_node, element, parser)
        yield self._yield_parsing_result(node, new_node)

    def _parse_type_var(self, node, hint, parser):
        try:
            global_node = parser.validator.globals[hint.__name__]
        except KeyError:
            global_node = yield nodes.UnionNode()
            if hint.__constraints__:
                for constraint in hint.__constraints__:
                    yield self._map_parser(global_node, constraint, parser)
            else:
                yield self._map_parser(global_node, typing.Any, parser)
            parser.validator.globals[hint.__name__] = global_node
            parser.validator.all_nodes.append(global_node)

        new_node = yield nodes.TypeVarNode()
        new_node.add_child(global_node)
        parser.validator.all_nodes.append(new_node)
        yield self._yield_parsing_result(node, new_node)

    def _parse_tuple(self, node, hint, parser):
        new_node = yield nodes.TupleNode()
        for element in hint.__tuple_params__:
            yield self._map_parser(new_node, element, parser)
        yield self._yield_parsing_result(node, new_node)

    def _yield_parsing_result(self, node, new_node):
        # Potentially reducing the runtime efficiency
        # Need some evidences to decide what to do
        # with this piece of code next
        if node:
            node.add_child(new_node)
        else:
            yield new_node