import ast
import uuid
import inspect
import textwrap

from yoloboros.grammar import transplainers
from yoloboros import constants


class Box:
    def __init__(self, value=None):
        self.__value = value

    def __call__(self):
        return self.__value

    def _set(self, value):
        self.__value = value


class ComponentMeta(type):
    def __new__(mcls, name, bases, attrs, app=None):
        attrs["requests"] = dict()
        attrs["responses"] = dict()
        if app:
            attrs["app"] = app
        else:
            attrs["app"] = next(filter(bool, (getattr(c, 'app', None) for c in bases)), None)

        if name in {'__yolo__component', '__yolo__root'}:
            return super(mcls, ComponentMeta).__new__(mcls, name, bases, attrs)

        return super(mcls, ComponentMeta).__new__(mcls, name, bases, attrs)


class BaseComponent:
    def __init__(self, state=None):
        self.state = state

    @classmethod
    def process(cls, data):
        identifier = data["identifier"]
        action = data["action"]
        request = data["request"]
        component = cls.registry[identifier]
        return component.responses[action](component, request)

    @classmethod
    def build(cls, app):
        for k, v in vars(cls).copy().items():
            if not k.startswith("_") and inspect.isgeneratorfunction(v) and k != 'render' and k != 'fetch':
                cls.requests[k], cls.responses[k] = app.action_renderer(
                    v.__name__, v
                ).build_funcs()
                delattr(cls, k)

        if hasattr(cls, 'fetch'):
            init, response_fetch = app.fetch_renderer(cls.identifier, cls.fetch).build_funcs()
            cls.responses.setdefault('fetch', response_fetch)
        elif hasattr(cls, 'init'):
            init = transplainers.JsTranslator(cls.init).walk()
            init.body[0].name = constants.COMPONENT_INIT
            init = textwrap.dedent(init.render())
        else:
            init = f"const {constants.COMPONENT_INIT} = () => null;\n"

        if hasattr(cls, 'render'):
            ns = dict(app=app)
            render = ast.fix_missing_locations(app.node_renderer(cls.render, namespace=ns).walk())
            render = transplainers.JsTranslator(render).walk().render()
            if actions := ns.get('actions'):
                for action, (request, response) in actions.items():
                    cls.requests.setdefault(action, request)
                    cls.responses.setdefault(action, response)
        else:
            render = f"const {constants.COMPONENT_RENDER} = () => null;\n"

        ret = textwrap.dedent(
            f"""(() => {{
            const {constants.COMPONENT_IDENTIFIER} = "{cls.identifier}";
            const {constants.COMPONENT_ACTIONS} = {{}};\n
            {textwrap.indent(init, '    ' * 3).lstrip(' ')}
            {textwrap.indent(render, '    ' * 3).lstrip(' ')}
            """
        ).lstrip()
        for k, v in cls.requests.items():
            if not isinstance(v, str):
                v = v.render()
            ret += textwrap.indent(f'{constants.COMPONENT_ACTIONS}["{k}"] = {v};\n', '    ' * 3)

        is_root = 'true' if cls.is_root else 'false'
        ret += '\n' + textwrap.indent(
            f"YOLO_COMPONENTS['{cls.__name__}'] = {constants.COMPONENT_MAKE_FULL.format(is_root=is_root)};\n",
            '    ' * 3
        )
        ret += '\n' + '    ' * 2 + '})();\n'
        return textwrap.indent(ret, '   ').lstrip(' ')

    def __init_subclass__(cls):
        if cls.__name__ not in {'__yolo__component', '__yolo__root'}:
            cls.identifier = str(len(cls.registry))
            cls.registry[cls.identifier] = cls


class AppicationMeta(type):
    def __new__(mcls, name, bases, attrs):
        box = Box()
        class __yolo__component(BaseComponent, metaclass=ComponentMeta, app=box):
            is_root = False
            registry = dict()

        class __yolo__root(__yolo__component):
            is_root = True

        attrs["_name"] = name
        attrs["component"] = __yolo__component
        attrs["root"] = __yolo__root
        ret = super(mcls, AppicationMeta).__new__(mcls, name, bases, attrs)
        box._set(ret)
        return ret


class BaseYoloboros:
    pass


class Yoloboros(BaseYoloboros, metaclass=AppicationMeta):
    pyodide: bool = False

    @classmethod
    def process(cls, data):
        return cls.component.process(data)

    @classmethod
    @property
    def code(cls):
        components = cls.component.registry.values()
        return ';\n'.join(c.build(cls) for c in components)

    @classmethod
    @property
    def node_renderer(cls):
        if cls.pyodide:
            return transplainers.PyodideNodeRenderer
        else:
            return transplainers.NodeRenderer

    @classmethod
    @property
    def action_renderer(cls):
        if cls.pyodide:
            return transplainers.PyodideActionRenderer
        else:
            return transplainers.ActionRenderer

    @classmethod
    @property
    def fetch_renderer(cls):
        if cls.pyodide:
            return transplainers.PyodideFetchRenderer
        else:
            return transplainers.FetchRenderer

    @classmethod
    def mount(cls, id):
        name = next((c.__name__ for c in cls.component.registry.values() if c.is_root), None)
        return cls.code + f'YOLO_COMPONENTS["{name}"].make().render("{id}")'
