import ast
import inspect
import textwrap

from yoloboros import grammar


class BaseRenderer(ast.NodeTransformer):
    def __init__(self, value):
        self.value = value

    def walk(self):
        if isinstance(self.value, str):
            obj = ast.parse(self.value)
        elif isinstance(self.value, ast.AST):
            obj = self.value
        else:
            obj = textwrap.dedent(inspect.getsource(self.value))
            stripped = obj.lstrip(" ")
            if stripped != obj:
                obj = stripped.replace("\n    ", "\n")
            obj = ast.parse(obj)
        return self.visit(obj)

    def get_source(self, obj):
        try:
            obj = inspect.getsource(obj)
        except:
            obj = getattr(obj, "__src")
        return textwrap.dedent(obj)


class JsTranslator(BaseRenderer):
    mapping = dict(reversed(pair) for pair in grammar.TABLE)

    def _visit_special(self, obj):
        match obj:
            case list():
                return list(map(self.visit, obj))
            case _:
                return obj

    def generic_visit(self, node):
        if target_node := self.mapping.get(type(node)):
            if fields := target_node._fields:
                attrs = {f: self.visit(getattr(node, f)) for f in fields}
                return target_node(**attrs)
            else:
                return target_node()
        else:
            return self._visit_special(node)


class NodeRenderer(BaseRenderer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_stack = []

    def visit(self, node):
        if hasattr(
            node, "_fields"
        ):  # Ensure this is an AST node and not a list or other iterable
            node.parent = self.parent_stack[-1] if self.parent_stack else None

        self.parent_stack.append(node)
        ret = super().visit(node)
        self.parent_stack.pop()
        return ret

    def visit_AnnAssign(self, node):
        method = "setAttribute"
        args = [ast.Constant(node.annotation.id), node.value]
        if isinstance(node.value, ast.Call):
            name = node.value.func.id
            if name == "call":
                method = "setCall"
            elif name == "action":
                method = "setAction"
            else:
                raise NotImplementedError(f"Unknown method {name}")
            args = [ast.Name(id="self"), *node.value.args]

        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=node.target.id, ctx=ast.Load()),
                attr=method,
                ctx=ast.Load(),
            ),
            args=args,
            keywords=[],
        )

    def visit_Constant(self, node):
        if (
            isinstance(node.value, str)
            and len(self.parent_stack) > 1
            and not isinstance(self.parent_stack[-2], ast.With)
        ):
            return ast.Call(
                func=ast.Name(id="__text", ctx=ast.Load()),
                args=[ast.Name(id="current", ctx=ast.Load()), ast.Constant(node.value)],
                keywords=[],
            )
        return node

    def visit_FormattedValue(self, node):
        return node

    def visit_JoinedStr(self, node):
        if len(self.parent_stack) > 1 and not isinstance(
            self.parent_stack[-2], ast.With
        ):
            values = [self.visit(value) for value in node.values]
            return ast.Call(
                func=ast.Name(id="__text", ctx=ast.Load()),
                args=[ast.Name(id="current", ctx=ast.Load()), ast.JoinedStr(values)],
                keywords=[],
            )
        return node

    def visit_FunctionDef(self, node):
        if node.name == "render":
            node.body = [self.visit(stmt) for stmt in node.body]
            node.args.args += [
                ast.keyword(arg="current", value=ast.Constant(None)),
            ]
            return node
        else:
            return ast.Module(
                body=[
                    node,
                    ast.Assign(
                        targets=[
                            ast.Attribute(
                                value=ast.Name(id="self"),
                                attr=ast.Attribute(
                                    value=ast.Name(id="namespace"),
                                    attr=node.name,
                                ),
                            )
                        ],
                        value=ast.Name(id=node.name, ctx=ast.Load()),
                    ),
                ],
                type_ignores=[],
            )

    def visit_With(self, node):
        if len(node.items) > 1:
            nested = ast.With(
                items=node.items[1:],
                body=node.body,
            )
            node.items = node.items[:1]
            node.body = [nested]
            return self.visit(node)

        if isinstance(node.items[0].context_expr, ast.Call):
            attrs = JsTranslator(
                ast.Dict(
                    keys=[
                        ast.Constant(key.arg)
                        for key in node.items[0].context_expr.keywords
                    ],
                    values=[
                        self.visit(value.value)
                        for value in node.items[0].context_expr.keywords
                    ],
                )
            ).walk()
            tag = node.items[0].context_expr.func.id
        else:
            attrs = grammar.JsConstant(None)
            tag = node.items[0].context_expr.id

        lambda_ = grammar.MultilineLambda(
            args=grammar.Jsarguments(
                posonlyargs=[],
                args=[grammar.JsName(id="current", ctx=ast.Load())],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=[JsTranslator(self.visit(stmt)).walk() for stmt in node.body],
        )

        body = [
            grammar.JsCall(
                func=grammar.JsName(id="__create_element", ctx=ast.Load()),
                args=[
                    grammar.JsConstant(tag),
                    attrs,
                    grammar.JsName(id="current"),
                    lambda_,
                ],
                keywords=[],
            )
        ]

        if node.items[0].optional_vars:
            name = node.items[0].optional_vars.id
            lambda_.body.insert(
                0,
                grammar.JsAssign(
                    targets=[grammar.JsName(id=name)],
                    value=grammar.JsCall(
                        func=grammar.JsName(id="__wrap", ctx=ast.Load()),
                        args=[grammar.JsName(id="current")],
                        keywords=[],
                    ),
                ),
            )

        return ast.Module(body=body, type_ignores=[])


class ActionRenderer(BaseRenderer):
    def __init__(self, action, value):
        super().__init__(value)
        self.action = action
        self.request = []
        self.response = []
        self.receive = []
        self.rest_args = None
        self.target = self.request

    def visit_Module(self, node):
        assert len(node.body) == 1
        self.visit(node.body[0])

    def visit_FunctionDef(self, node):
        self.rest_args = node.args.args
        for stmt in node.body:
            self.visit(stmt)

    def generic_visit(self, node):
        # TODO
        # consider this
        # if ...:
        #     yield
        # else:
        #     yield
        #
        # should mark topmost statement as yield
        match node:
            case ast.Assign(
                targets=[ast.Name(id="request", ctx=ast.Store())], value=ast.Yield()
            ):
                self.target.append(ast.Return(value=node.value.value))
                self.target = self.response
            case ast.Assign(
                targets=[ast.Name(id="response", ctx=ast.Store())], value=ast.Yield()
            ):
                self.target.append(ast.Return(value=node.value.value))
                self.target = self.receive
            case _:
                self.target.append(node)

    def build_funcs(self):
        self.walk()

        inner_request_func_name = f"inner_request_{self.action}"
        request_func_name = f"request_{self.action}"
        receive_func_name = f"receive_{self.action}"

        inner_request_func = ast.Module(
            body=[
                ast.FunctionDef(
                    name=inner_request_func_name,
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                    ),
                    body=self.request,
                    decorator_list=[],
                )
            ],
            type_ignores=[],
        )

        receive_func = ast.Module(
            body=[
                ast.FunctionDef(
                    name=receive_func_name,
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[ast.arg(arg="request"), ast.arg(arg="response")],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                    ),
                    body=self.receive or [ast.Pass()],
                    decorator_list=[],
                )
            ],
            type_ignores=[],
        )

        request_func = ast.Module(
            body=[
                ast.FunctionDef(
                    name=request_func_name,
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[ast.Name(id="self")],
                        vararg=ast.arg("args"),
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                    ),
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id="__action", ctx=ast.Store())],
                            value=ast.Constant(self.action),
                        ),
                        inner_request_func,
                        receive_func,
                        ast.Return(
                            ast.Call(
                                func=ast.Name(id="__fetch", ctx=ast.Load()),
                                args=[
                                    ast.Name(id="identifier", ctx=ast.Load()),
                                    ast.Name(id="__action", ctx=ast.Load()),
                                    ast.Name(
                                        id=inner_request_func_name, ctx=ast.Load()
                                    ),
                                    ast.Name(id=receive_func_name, ctx=ast.Load()),
                                    ast.Starred(
                                        value=ast.Name(id="args", ctx=ast.Load())
                                    ),
                                ],
                                keywords=[],
                            )
                        ),
                    ],
                    decorator_list=[],
                )
            ],
            type_ignores=[],
        )

        response_func = ast.Module(
            body=[
                ast.FunctionDef(
                    name=f"response_{self.action}",
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[ast.arg(arg="request")],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                    ),
                    body=self.response,
                    decorator_list=[],
                )
            ],
            type_ignores=[],
        )

        request_func = ast.fix_missing_locations(request_func)
        response_func = ast.fix_missing_locations(response_func)
        ns = {}
        exec(ast.unparse(response_func), ns)
        return (JsTranslator(request_func).walk().render(), ns.popitem()[1])
