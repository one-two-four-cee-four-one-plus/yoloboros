import ast
import uuid
import inspect
import textwrap

from yoloboros.transformer import JsTranslator, NodeRenderer, ActionRenderer, FetchRenderer
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

        for k, v in attrs.copy().items():
            if not k.startswith("_") and inspect.isgeneratorfunction(v) and k != 'render' and k != 'fetch':
                attrs["requests"][k], attrs["responses"][k] = ActionRenderer(
                    v.__name__, v
                ).build_funcs(use_pyodide=attrs['app']().pyodide)
                del attrs[k]

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
    def build(cls):
        if hasattr(cls, 'fetch'):
            init, response_fetch = FetchRenderer(cls.identifier, cls.fetch).build_funcs(use_pyodide=cls.app().pyodide)
            cls.responses.setdefault('fetch', response_fetch)
        elif hasattr(cls, 'init'):
            init = JsTranslator(cls.init).walk()
            init.body[0].name = constants.COMPONENT_INIT
            init = textwrap.dedent(init.render())
        else:
            init = f"const {constants.COMPONENT_INIT} = () => null;\n"

        if hasattr(cls, 'render'):
            ns = dict(app=cls.app())
            render = ast.fix_missing_locations(NodeRenderer(cls.render, namespace=ns).walk())
            render = JsTranslator(render).walk().render()
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
            ret += textwrap.indent(f'__yolo__actions["{k}"] = {v};\n', '    ' * 3)

        ret += '\n' + textwrap.indent(
            (
                f"const ret = {constants.COMPONENT_MAKE_FULL};\n"
                f"YOLO_COMPONENTS['{cls.__name__}'] = ret;\n"
                "return ret;"
            ),
            '    ' * 3
        )
        ret += '\n' + '    ' * 2 + '})()'
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
    packages: list = []
    vdom: bool = False

    @classmethod
    def process(cls, data):
        return cls.component.process(data)

    @classmethod
    @property
    def code(cls):
        packages = ''
        if cls.pyodide and cls.packages:
            packages += 'await window.pyodide.loadPackage("micropip");\n'
            packages += 'const micropip = window.pyodide.pyimport("micropip");\n'
            for package_name in cls.packages:
                packages += f'await micropip.install("{package_name}");\n'

        components = cls.component.registry.values()
        return packages + ';\n'.join(c.build() for c in components)

    @classmethod
    def mount(cls, id):
        name = next((c.__name__ for c in cls.component.registry.values() if c.is_root), None)
        return cls.code + f'\nYOLO_COMPONENTS["{name}"].render("{id}")'
