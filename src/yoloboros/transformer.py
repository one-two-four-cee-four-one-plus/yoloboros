import ast
import hashlib
import inspect
import textwrap

from yoloboros import grammar, constants


def pyodidize(body, locals=None, globals=None):
    if isinstance(body[-1], ast.Return):
        body[-1] = body[-1].value
    for i, v in enumerate(body.copy()):
        if isinstance(v, ast.Expr) and isinstance(v.value, ast.Constant) and isinstance(v.value.value, str):
            body[i] = ast.Expr(
                call(
                    func=ast.Name(id=constants.COMPONENT_TEXT),
                    args=[ast.Name(id="current"), v.value]
                )
            )
        elif isinstance(v, ast.Expr) and isinstance(v.value, ast.JoinedStr):
            body[i] = ast.Expr(
                call(
                    func=ast.Name(id=constants.COMPONENT_TEXT),
                    args=[ast.Name(id="current"), v.value]
                )
            )
    body = ast.Module(body=body, type_ignores=[])
    body = ast.unparse(ast.fix_missing_locations(body))
    args = [grammar.MultilineConstant(value=body)]
    if locals and isinstance(locals, dict):
        items = locals.items()
        args.append(
            ast.Dict(
                keys=[ast.Constant('locals')],
                values=[
                    call(
                        func=ast.Attribute(value=pyodide, attr='toPy'),
                        args=[ast.Dict(keys=[i[0] for i in items], values=[i[1] for i in items])],
                    )
                ]
            )
        )
    elif locals:
        args.append(
            ast.Dict(
                keys=[ast.Constant('locals')],
                values=[locals]
            )
        )

    if globals and isinstance(globals, dict):
        items = globals.items()
        args.append(
            ast.Dict(
                keys=[ast.Constant('globals')],
                values=[
                    call(
                        func=ast.Attribute(value=pyodide, attr='toPy'),
                        args=[ast.Dict(keys=[i[0] for i in items], values=[i[1] for i in items])],
                    )
                ]
            )
        )
    elif globals:
        args.append(
            ast.Dict(
                keys=[ast.Constant('globals')],
                values=[globals]
            )
        )

    return call(
        func=ast.Attribute(
            value='pyodide',
            attr='runPython'
        ),
        args=args
    )


def arguments(cls=ast.arguments, **kwargs):
    return cls(
        posonlyargs=kwargs.get('posonlyargs', []),
        args=kwargs.get('args', []),
        vararg=kwargs.get('vararg', []),
        kwonlyargs=kwargs.get('kwonlyargs', []),
        kw_defaults=kwargs.get('kw_defaults', []),
        defaults=kwargs.get('defaults', []),
    )


def js_arguments(**kwargs):
    return arguments(cls=grammar.Jsarguments, **kwargs)


def call(**kwargs):
    return ast.Call(
        func=kwargs['func'],
        args=kwargs.get('args', []),
        keywords=kwargs.get('keywords', []),
    )


def function(**kwargs):
    return ast.FunctionDef(
        name=kwargs['name'],
        args=kwargs.get('args', []),
        body=kwargs['body'],
        decorator_list=kwargs.get('decorator_list', []),
    )

def module(*body):
    return ast.Module(body=body, type_ignores=[])


class BaseRenderer(ast.NodeTransformer):
    def __init__(self, value, namespace=None):
        self.value = value
        self.namespace = namespace or dict()

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
        if app := self.namespace.get('app'):
            self.pyodide = app().pyodide
        else:
            self.pyodide = False
        self.parent_stack = []
        self.with_stack = []

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
        if isinstance(node.annotation, ast.Name):
            args = [ast.Constant(node.annotation.id), node.value]
        else:
            args = [ast.Constant(node.annotation.value), node.value]

        if isinstance(node.value, ast.Call):
            name = node.value.func.id
            if name == "call":
                method = "setCall"
            elif name == "action":
                method = "setAction"
            else:
                raise NotImplementedError(f"Unknown method {name}")
            if isinstance(node.annotation, ast.Name):
                args = [ast.Name(id="self"), ast.Constant(node.annotation.id), *node.value.args]
            else:
                args = [ast.Name(id="self"), ast.Constant(node.annotation.value), *node.value.args]

        return call(
            func=ast.Attribute(
                value=ast.Name(id=node.target.id),
                attr=method,
                ctx=ast.Load(),
            ),
            args=args,
        )

    def visit_Constant(self, node):
        if (
            not self.pyodide
            and isinstance(node.value, str)
            and len(self.parent_stack) > 1
            and not isinstance(self.parent_stack[-2], ast.With)
            and not getattr(self, '_visiting_JoinedStr', False)
        ):
            return call(
                func=ast.Name(id=constants.COMPONENT_TEXT),
                args=[
                    ast.Name(id="current"),
                    # todo: write parser using https://docs.python.org/3/library/html.parser.html
                    ast.Constant(
                        textwrap.dedent(node.value).replace("\n", "<br>")
                        .replace('"', "'").replace(" ", "&nbsp;")
                    )
                ],
            )
        return node

    def visit_FormattedValue(self, node):
        return node

    def visit_JoinedStr(self, node):
        if (
                not self.pyodide
                and len(self.parent_stack) > 1
                and not isinstance(self.parent_stack[-2], ast.With)
                and not getattr(self, '_visiting_JoinedStr', False)
        ):
            setattr(self, '_visiting_JoinedStr', True)
            values = [self.visit(value) for value in node.values]
            delattr(self, '_visiting_JoinedStr')
            return ast.Call(
                func=ast.Name(id=constants.COMPONENT_TEXT),
                args=[ast.Name(id="current"), ast.JoinedStr(values)],
                keywords=[],
            )
        return node

    def pyodidize_body(self, node_body):
        body = []
        stmts = []
        locals = ast.Name(id=constants.COMPONENT_LOCALS)
        for stmt in node_body:
            if isinstance(stmt, ast.With):
                if stmts:
                    body.append(pyodidize(stmts, locals=locals))
                    stmts.clear()
                body.append(stmt)
            else:
                stmts.append(stmt)
        if stmts:
            body.append(pyodidize(stmts, locals=locals))
        return body

    def visit_FunctionDef(self, node):
        if node.name == "render":
            node.name = constants.COMPONENT_RENDER
            if app := self.namespace.get("app"):
                if app().pyodide:
                    node.body = self.pyodidize_body(node.body)
                    node.body.insert(
                        0,
                        ast.Assign(
                            targets=[ast.Name(id=constants.COMPONENT_LOCALS)],
                            value=call(
                                func=ast.Attribute(
                                    value=ast.Name(id="pyodide"),
                                    attr='toPy',
                                ),
                                args=[
                                    ast.Dict(
                                        keys=[ast.Constant(constants.COMPONENT_TEXT), ast.Constant('current')],
                                        values=[ast.Name(id=constants.COMPONENT_TEXT), ast.Name(id='current')]
                                    )
                                ],
                            )
                        )
                    )

            node.body = [self.visit(stmt) if isinstance(stmt, ast.With) else stmt for stmt in node.body]
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
                        value=ast.Name(id=node.name),
                    ),
                ],
                type_ignores=[],
            )

    def visit_With(self, node):
        self.with_stack.append(node)
        if app := self.namespace.get("app"):
           if app().pyodide:
               node.body = self.pyodidize_body(node.body)
        ret = self._visit_With(node)
        self.with_stack.pop()
        return ret

    def inlined_with(self, node):
        if any(isinstance(node, ast.Yield) for node in ast.walk(node)):
            func_def = function(
                name="inlined_with",
                args=arguments(),
                body=node.body,
            )
            unparsed = ast.unparse(ast.fix_missing_locations(func_def))
            name = f'anon_{hashlib.md5(unparsed.encode()).hexdigest()}'
            request, response = ActionRenderer(name, unparsed).build_funcs(text_request=False)
            self.namespace.setdefault("actions", {})[name] = JsTranslator(request).walk().render(), response
            lambda_ = request
        else:
            lambda_ = grammar.MultilineLambda(
                args=js_arguments(
                    args=(
                        [grammar.JsName(id=node.items[0].optional_vars.id)]
                        if node.items[0].optional_vars
                        else []
                    ),
                ),
                body=[JsTranslator(self.visit(stmt)).walk() for stmt in node.body],
            )

        return grammar.JsCall(
            func=grammar.JsName(id=constants.COMPONENT_ADD_EVENT_LISTENER),
            args=[
                JsTranslator(node.items[0].context_expr.value).walk(),
                grammar.JsConstant(node.items[0].context_expr.attr.lstrip('on')),
                lambda_
            ],
            keywords=[],
        )

    def _visit_With(self, node):
        if len(node.items) > 1:
            nested = ast.With(
                items=node.items[1:],
                body=node.body,
            )
            node.items = node.items[:1]
            node.body = [nested]
            return self.visit(node)

        components = [c.__name__ for c in self.namespace['app']().component.registry.values()]
        bindings = [getattr(w.items[0].optional_vars, 'id', None) for w in self.with_stack[:-1]]

        match node.items[0].context_expr:
            case ast.Call():
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
            case ast.Attribute() if node.items[0].context_expr.attr in components:
                attrs = grammar.JsConstant(None)
                tag = 'yolo:' + node.items[0].context_expr.attr
            case ast.Name() if node.items[0].context_expr.id in components:
                attrs = grammar.JsConstant(None)
                tag = 'yolo:' + node.items[0].context_expr.id
            case ast.Attribute() if node.items[0].context_expr.value.id in bindings:
                return self.inlined_with(node)
            case _:
                attrs = grammar.JsConstant(None)
                tag = node.items[0].context_expr.id

        lambda_ = grammar.MultilineLambda(
            args=js_arguments(
                args=[grammar.JsName(id="current")],
            ),
            body=[JsTranslator(self.visit(stmt)).walk() for stmt in node.body],
        )

        body = [
            grammar.JsCall(
                func=grammar.JsName(id=constants.COMPONENT_NODE_CREATE, ctx=ast.Load()),
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
                        func=grammar.JsName(id=constants.COMPONENT_WRAP, ctx=ast.Load()),
                        args=[grammar.JsName(id="current")],
                        keywords=[],
                    ),
                ),
            )

        return ast.Module(body=body, type_ignores=[])


class ActionRenderer(BaseRenderer):
    def __init__(self, action, value, **kwargs):
        super().__init__(value, **kwargs)
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

    def build_funcs(self, text_request=True, use_pyodide=False):
        self.walk()

        if use_pyodide:
            if isinstance(self.request[-1], ast.Return):
                self.request[-1] = self.request[-1].value
            self.request = ast.Module(body=self.request, type_ignores=[])
            self.request = ast.unparse(ast.fix_missing_locations(self.request))
            self.request = [ast.Return(
                value=call(
                    func=ast.Attribute(
                        value=ast.Name(id='pyodide'),
                        attr='runPython'
                    ),
                    args=[grammar.MultilineConstant(value=self.request)],
                )
            )]

            if isinstance(self.receive[-1], ast.Return):
                self.receive[-1] = self.receive[-1].value
            self.receive = ast.Module(body=self.receive, type_ignores=[])
            self.receive = ast.unparse(ast.fix_missing_locations(self.receive))
            self.receive = [ast.Return(
                value=call(
                    func=ast.Attribute(
                        value=ast.Name(id='pyodide'),
                        attr='runPython'
                    ),
                    args=[
                        grammar.MultilineConstant(value=self.receive),
                        ast.Dict(
                            keys=[ast.Constant('locals')],
                            values=[
                                call(
                                    func=ast.Attribute(
                                        value=ast.Name(id='pyodide'),
                                        attr='toPy'
                                    ),
                                    args=[
                                        ast.Dict(
                                            keys=[ast.Constant(i) for i in ('request', 'response', 'self')],
                                            values=[ast.Name(id=i) for i in ('request', 'response', 'self')]
                                        )
                                    ],
                                )
                            ]
                        )
                    ],
                )
            )]

        inner_request_func = JsTranslator(ast.Module(
            body=[
                grammar.MultilineLambda(
                    args=arguments(),
                    body=self.request,
                )
            ],
            type_ignores=[],
        )).walk()

        receive_func = ast.Module(
            body=[
                grammar.MultilineLambda(
                    args=arguments(args=[ast.arg(arg="request"), ast.arg(arg="response")]),
                    body=self.receive or [ast.Pass()],
                )
            ],
            type_ignores=[],
        )

        request_func = ast.Module(
            body=[
                grammar.MultilineLambda(
                    args=arguments(
                        args=self.rest_args,
                        vararg=ast.arg("args"),
                    ),
                    body=[
                        ast.Return(
                            call(
                                func=ast.Name(id=constants.COMPONENT_FETCH, ctx=ast.Load()),
                                args=[
                                    ast.Name(id=constants.COMPONENT_IDENTIFIER, ctx=ast.Load()),
                                    ast.Constant(self.action),
                                    inner_request_func,
                                    receive_func,
                                ]
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
                function(
                    name=f"response_{self.action}",
                    args=arguments(
                        args=[
                            ast.arg(arg="self"),
                            ast.arg(arg="request")
                        ],
                    ),
                    body=self.response,
                )
            ],
            type_ignores=[],
        )

        request_func = ast.fix_missing_locations(request_func)
        response_func = ast.fix_missing_locations(response_func)

        if text_request:
            request_func = JsTranslator(request_func).walk().render()
        else:
            request_func = JsTranslator(request_func).walk()

        ns = {}
        exec(ast.unparse(response_func), ns)
        return (request_func,ns.popitem()[1])


class FetchRenderer(ActionRenderer):
    def __init__(self, identifier, value, **kwargs):
        super().__init__('fetch', value)
        self.identifier = identifier
        self.target = self.response

    def build_funcs(self, use_pyodide=False):
        self.walk()

        response_func = ast.Module(
            body=[
                function(
                    name=f"response_{self.action}",
                    args=arguments(
                        args=[
                            ast.arg(arg="self"),
                            ast.arg(arg="request")
                        ],
                    ),
                    body=self.response,
                )
            ],
            type_ignores=[],
        )

        state_update = ast.Assign(
            targets=[
                ast.Attribute(
                    value=ast.Name(id="self"),
                    attr='state'
                )
            ],
            value=ast.Name(id='response', ctx=ast.Load()),
        )
        if self.receive:
            self.receive.insert(
                0,
                state_update
            )
        else:
            self.receive = [state_update]

        if use_pyodide:
            if isinstance(self.receive[-1], ast.Return):
                self.receive[-1] = self.receive[-1].value
            self.receive = ast.Module(body=self.receive, type_ignores=[])
            self.receive = ast.unparse(ast.fix_missing_locations(self.receive))
            self.receive = [ast.Return(
                value=call(
                    func=ast.Attribute(
                        value=ast.Name(id='pyodide'),
                        attr='runPython'
                    ),
                    args=[
                        grammar.MultilineConstant(value=self.receive),
                        ast.Dict(
                            keys=[ast.Constant('locals')],
                            values=[
                                call(
                                    func=ast.Attribute(
                                        value=ast.Name(id='pyodide'),
                                        attr='toPy'
                                    ),
                                    args=[
                                        ast.Dict(
                                            keys=[ast.Constant(i) for i in ('request', 'response', 'self')],
                                            values=[ast.Name(id=i) for i in ('request', 'response', 'self')]
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                )
            )]

        receive_func = JsTranslator(ast.Module(
            body=[
                grammar.MultilineLambda(
                    args=arguments(
                        args=[ast.arg(arg="request"), ast.arg(arg="response")],
                    ),
                    body=self.receive,
                )
            ],
            type_ignores=[],
        )).walk()

        request_func = JsTranslator(ast.Module(
            body=[
                function(
                    name=constants.COMPONENT_INIT,
                    args=arguments(
                        args=self.rest_args,
                        vararg=ast.arg("args"),
                    ),
                    body=[
                        ast.Return(
                            call(
                                func=ast.Name(id=constants.COMPONENT_FETCH, ctx=ast.Load()),
                                args=[
                                    ast.Name(id=constants.COMPONENT_IDENTIFIER, ctx=ast.Load()),
                                    ast.Constant(self.action),
                                    grammar.MultilineLambda(
                                        args=arguments(),
                                        body=[ast.Return(value=ast.Dict(keys=[], values=[]))]
                                    ),
                                    receive_func,
                                ],
                            )
                        ),
                    ]
                )
            ],
            type_ignores=[],
        )).walk()

        request_func = ast.fix_missing_locations(request_func)
        response_func = ast.fix_missing_locations(response_func)
        ns = {}
        exec(ast.unparse(response_func), ns)
        return (
            JsTranslator(request_func).walk().render(),
            ns.popitem()[1]
        )
