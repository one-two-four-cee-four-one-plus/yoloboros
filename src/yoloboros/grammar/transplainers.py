import ast
import uuid
import hashlib
import inspect
import textwrap
import html.parser

from yoloboros.grammar import syntax as grammar
from yoloboros import constants


class HTMLRenderer(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = ''

    def handle_starttag(self, tag, attrs):
        self.result += f'<{tag} {self._attrs(attrs)}>'

    def _attrs(self, attrs):
        ret = []
        for k, v in attrs:
            if '"' in v:
                v = v.replace('"', "'")
                ret.append(f'{k}={v}')
            else:
                ret.append(f"{k}='{v}'")
        return ' '.join(ret)

    def handle_endtag(self, tag):
        self.result += f'</{tag}>'

    def handle_data(self, data):
        self.result += data.replace("\n", "<br>").replace('"', "'").replace(" ", "&nbsp;")

    @classmethod
    def render(self, value):
        renderer = HTMLRenderer()
        renderer.feed(textwrap.dedent(value))
        return renderer.result


def tag_children(node):
    for child in ast.iter_child_nodes(node):
        child.parent = node
        for attr in node._fields:
            if isinstance(getattr(node, attr), list) and child in getattr(node, attr):
                child.parent_attr = attr
                child.parent_attr_idx = getattr(node, attr).index(child)
            elif child == getattr(node, attr):
                child.parent_attr = attr
                child.parent_attr_idx = None

        tag_children(child)


class Node:
    def __init__(self, value, **kwargs):
        self.value = ast.parse(value)
        tag_children(self.value)
        self.kwargs = kwargs

    def replace(self, replacement, target=None):
        if target is not None:
            replacement, target = target, replacement
        elif target is None:
            target = lambda x: isinstance(x, ast.Ellipsis)

        if not callable(target):
            target = lambda x: x == target

        node = next(i for i in ast.walk(self.value) if target(i))
        if node.parent_attr_idx is not None:
            getattr(node.parent, node.parent_attr)[node.parent_attr_idx] = replacement
        else:
            setattr(node.parent, node.parent_attr, replacement)

    def __call__(self, *args, **kwargs):
        self.replace(*args, **kwargs)
        return self

    def as_exp(self):
        return ast.Expr(self.value)

    def as_mod(self):
        return ast.Module(body=[self.value], type_ignores=[])

    def as_js(self):
        return JsTranslator(self.value).walk()

    def val(self):
        return self.value

    @classmethod
    def dict(self, d):
        items = d.items() if isinstance(d, dict) else d
        return ast.Dict(keys=[i[0] for i in items], values=[i[1] for i in items])

    @classmethod
    def c(self, value):
        return ast.Constant(value=value)

    @classmethod
    def n(self, id):
        return ast.Name(id=id)

    @classmethod
    def a(self, **kwargs):
        return ast.arguments(
            posonlyargs=kwargs.get('posonlyargs', []),
            args=kwargs.get('args', []),
            vararg=kwargs.get('vararg', []),
            kwonlyargs=kwargs.get('kwonlyargs', []),
            kw_defaults=kwargs.get('kw_defaults', []),
            defaults=kwargs.get('defaults', []),
        )

    @classmethod
    def js_a(self, **kwargs):
        return grammar.Jsarguments(
            posonlyargs=kwargs.get('posonlyargs', []),
            args=kwargs.get('args', []),
            vararg=kwargs.get('vararg', []),
            kwonlyargs=kwargs.get('kwonlyargs', []),
            kw_defaults=kwargs.get('kw_defaults', []),
            defaults=kwargs.get('defaults', []),
        )

    @classmethod
    def f(self, **kwargs):
        return ast.FunctionDef(
            name=kwargs['name'],
            args=kwargs.get('args', []),
            body=kwargs['body'],
            decorator_list=kwargs.get('decorator_list', []),
        )

    @classmethod
    def js(self, value):
        return JsTranslator(value).walk()


_ = Node


def pyodidize(body, locals=None, globals=None):
    if isinstance(body[-1], ast.Return):
        body[-1] = body[-1].value
    for i, v in enumerate(body.copy()):
        match v:
            case ast.Expr(ast.Constant(str(value))) | ast.Expr(ast.JoinedStr(value)):
                body[i] = _(f'{constants.COMPONENT_TEXT}(current, ...)')(v.value).as_exp()
    codeblock = ast.Module(body=body, type_ignores=[])
    args = [grammar.MultilineConstant(value=ast.unparse(ast.fix_missing_locations(codeblock)))]
    if locals and isinstance(locals, dict):
        args.append(_('{"locals": pyodide.toPy(...)}')(_.dict(locals)).val())
    elif locals:
        args.append(_('{"locals": ...}')(locals).val())

    if globals and isinstance(globals, dict):
        args.append(_('{"globals": pyodide.toPy(...)}')(_.dict(globals)).val())
    elif globals:
        args.append(_('{"globals": ...}')(globals).val())

    return call(func=_('pyodide.runPython').val(), args=args)


def call(**kwargs):
    return ast.Call(
        func=kwargs['func'],
        args=kwargs.get('args', []),
        keywords=kwargs.get('keywords', []),
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
        self.with_stack = []

    def visit_Expr(self, node):
        match node:
            case ast.Expr(ast.Constant(str(value))) if not self.pyodide:
                const = ast.Constant(HTMLRenderer().render(value))
                return _(f'{constants.COMPONENT_TEXT}(current, ...)')(const).val()
            case ast.Expr(ast.JoinedStr(value)) if not self.pyodide:
                for i, v in enumerate(value):
                    if isinstance(v, ast.Constant):
                        value[i].value = HTMLRenderer().render(v.value)
                return _(f'{constants.COMPONENT_TEXT}(current, ...)')(ast.JoinedStr(value)).val()
            case _:
                return node

    def pyodidize_body(self, node_body):
        body, stmts = [], []
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
            if self.pyodide:
                node.body = self.pyodidize_body(node.body)
                dict_ = _.dict([
                    (_.c(constants.COMPONENT_TEXT), _.n(id=constants.COMPONENT_TEXT)),
                    (_.c('current'), _.n(id='current')),
                    (_.c('self'), _.n(id='self'))
                ])
                node.body.insert(0, _(f'{constants.COMPONENT_LOCALS} = pyodide.toPy(...)')(dict_).val())
                node.body = [self.visit(stmt) if isinstance(stmt, ast.With) else stmt for stmt in node.body]
            else:
                node.body = [self.visit(stmt) for stmt in node.body]
            node.args.args += [ast.keyword(arg="current", value=ast.Constant(None))]
            return node
        else:
            return module(
                node,
                _(f'self.namespace.{node.name} = {node.name}').val()
            )

    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)

    def visit_With(self, node):
        self.with_stack.append(node)
        if self.pyodide:
            node.body = self.pyodidize_body(node.body)
        ret = self._visit_With(node)
        self.with_stack.pop()
        return ret

    def inlined_with(self, node):
        if any(isinstance(node, ast.Yield) for node in ast.walk(node)):
            func_def = _.f(
                name="inlined_with",
                args=_.a(),
                body=node.body,
            )
            unparsed = ast.unparse(ast.fix_missing_locations(func_def))
            name = f'anon_{hashlib.md5(unparsed.encode()).hexdigest()}'
            request, response = ActionRenderer(name, unparsed).build_funcs(text_request=False)
            self.namespace.setdefault("actions", {})[name] = JsTranslator(request).walk().render(), response
            lambda_ = request
        else:
            lambda_ = grammar.MultilineLambda(
                args=_.js_a(
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
            nested = ast.With(items=node.items[1:], body=node.body)
            node.items = node.items[:1]
            node.body = [nested]
            return self.visit(node)

        components = [c.__name__ for c in self.namespace['app']().component.registry.values()]
        bindings = [getattr(w.items[0].optional_vars, 'id', None) for w in self.with_stack[:-1]]

        item = node.items[0]
        match item.context_expr:
            case ast.Call():
                attrs = JsTranslator(
                    ast.Dict(
                        keys=[ast.Constant(key.arg) for key in item.context_expr.keywords],
                        values=[self.visit(value.value) for value in item.context_expr.keywords],
                    )
                ).walk()
                tag = item.context_expr.func.id
            case ast.Attribute() if item.context_expr.attr in components:
                attrs = grammar.JsConstant(None)
                tag = 'yolo:' + item.context_expr.attr
            case ast.Name() if item.context_expr.id in components:
                attrs = grammar.JsConstant(None)
                tag = 'yolo:' + item.context_expr.id
            case ast.Attribute() if item.context_expr.value.id in bindings:
                return self.inlined_with(node)
            case _:
                attrs = grammar.JsConstant(None)
                tag = item.context_expr.id

        lambda_ = grammar.MultilineLambda(
            args=_.js_a(args=[grammar.JsName(id="current")]),
            body=[JsTranslator(self.visit(stmt)).walk() for stmt in node.body],
        )

        body = [
            grammar.JsCall(
                func=grammar.JsName(id=constants.COMPONENT_NODE_CREATE),
                args=[
                    grammar.JsConstant(tag),
                    grammar.JsConstant(str(uuid.uuid4())),
                    attrs,
                    grammar.JsName(id="current"),
                    lambda_,
                ],
                keywords=[],
            )
        ]

        if item.optional_vars:
            name = item.optional_vars.id
            lambda_.body.insert(0, _(f'{name} = {constants.COMPONENT_WRAP}(current)').as_js())
            if self.pyodide:
                lambda_.body.insert(0, _(
                    f'{constants.COMPONENT_LOCALS}.set("{name}", {constants.COMPONENT_WRAP}(current))'
                ).as_js())
                lambda_.body.insert(0, _(
                    f'{constants.COMPONENT_LOCALS}.set("current", current)'
                ).as_js())

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
        if app := self.namespace.get('app'):
            self.pyodide = app().pyodide
        else:
            self.pyodide = False

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
        #     request = yield {}
        # else:
        #     request = yield {}
        #
        # should mark topmost statement as yield
        req, res = ast.Name(id="request"), ast.Name(id="response")
        match node:
            case ast.Assign(targets=[req], value=ast.Yield()) | ast.Yield(value=req):
                self.target.append(ast.Return(value=node.value.value))
                self.target = self.response
            case ast.Assign(targets=[res], value=ast.Yield()) | ast.Yield(value=res):
                self.target.append(ast.Return(value=node.value.value))
                self.target = self.receive
            case _:
                self.target.append(node)

    def build_funcs(self, text_request=True):
        self.walk()

        if self.pyodide:
            self.request = pyodidize(self.request)
            self.receive = pyodidize(self.request)

        request_func = module(
            grammar.MultilineLambda(
                args=_.js(_.a(args=self.rest_args, vararg=ast.arg("args"))),
                body=[
                    _.js(ast.Return(
                        call(
                            func=ast.Name(id=constants.COMPONENT_FETCH),
                            args=[
                                ast.Name(id=constants.COMPONENT_IDENTIFIER),
                                ast.Constant(self.action),
                                grammar.MultilineLambda(
                                    args=_.a(),
                                    body=self.request,
                                ),
                                grammar.MultilineLambda(
                                    args=_.a(args=[ast.arg(arg="request"), ast.arg(arg="response")]),
                                    body=self.receive,
                                ),
                            ]
                        )
                    )),
                ]
            )
        )

        response_func = _.f(
            name=f"response_{self.action}",
            args=_.a(
                args=[
                    ast.arg(arg="self"),
                    ast.arg(arg="request")
                ],
            ),
            body=self.response,
        )


        request_func = ast.fix_missing_locations(request_func)
        response_func = ast.fix_missing_locations(response_func)

        request_func = JsTranslator(request_func).walk()
        ns = {}
        exec(ast.unparse(response_func), ns)

        return (request_func, ns.popitem()[1])


class FetchRenderer(ActionRenderer):
    def __init__(self, identifier, value, **kwargs):
        super().__init__('fetch', value)
        self.identifier = identifier
        self.target = self.response

    def build_funcs(self, use_pyodide=False):
        self.walk()

        response_func = _.f(
            name=f"response_{self.action}",
            args=_.a(
                args=[
                    ast.arg(arg="self"),
                    ast.arg(arg="request")
                ],
            ),
            body=self.response,
        )

        if self.receive:
            self.receive.insert(
                0,
                _('self.state = response').val()
            )
        else:
            self.receive = [_('self.state = response').val()]

        if self.pyodide:
            self.receive = pyodidize(self.receive)

        receive_func = grammar.MultilineLambda(
            args=_.a(
                args=[ast.arg(arg="request"), ast.arg(arg="response")],
            ),
            body=self.receive,
        )

        request_func = _.f(
            name=constants.COMPONENT_INIT,
            args=_.a(
                args=self.rest_args,
                vararg=ast.arg("args"),
            ),
            body=[
                ast.Return(
                    call(
                        func=ast.Name(id=constants.COMPONENT_FETCH),
                        args=[
                            ast.Name(id=constants.COMPONENT_IDENTIFIER),
                            ast.Constant(self.action),
                            grammar.MultilineLambda(
                                args=_.a(),
                                body=[ast.Return(value=ast.Dict(keys=[], values=[]))]
                            ),
                            receive_func,
                        ],
                    )
                ),
            ]
        )

        request_func = ast.fix_missing_locations(request_func)
        response_func = ast.fix_missing_locations(response_func)
        ns = {}
        exec(ast.unparse(response_func), ns)
        return (
            JsTranslator(request_func).walk().render(),
            ns.popitem()[1]
        )
