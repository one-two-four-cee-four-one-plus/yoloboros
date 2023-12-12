import ast
import uuid
import inspect
import textwrap

from yoloboros.transformer import JsTranslator, NodeRenderer, ActionRenderer
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

        if name == '__yolo__component':
            return super(mcls, ComponentMeta).__new__(mcls, name, bases, attrs)

        if render := attrs.get("render"):
            ns = dict(app=attrs['app'])
            render = ast.fix_missing_locations(NodeRenderer(render, namespace=ns).walk())
            attrs["render"] = JsTranslator(render).walk().render()
        else:
            attrs["render"] = f"const {constants.COMPONENT_RENDER} = () => null;\n"

        if init := attrs.get("init"):
            init = JsTranslator(init).walk()
            init.body[0].name = constants.COMPONENT_INIT
            attrs["init"] = textwrap.dedent(init.render())
        else:
            attrs["init"] = f"const {constants.COMPONENT_INIT} = () => null;\n"

        for k, v in attrs.copy().items():
            if not k.startswith("_") and inspect.isgeneratorfunction(v):
                attrs["requests"][k], attrs["responses"][k] = ActionRenderer(
                    v.__name__, v
                ).build_funcs()
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
        return cls.registry[identifier].responses[action](request)

    @classmethod
    def build(cls):
        ret = textwrap.dedent(
            f"""(() => {{
            const {constants.COMPONENT_IDENTIFIER} = "{cls.identifier}";
            const {constants.COMPONENT_ACTIONS} = {{}};\n
            {textwrap.indent(cls.init, '    ' * 3).lstrip(' ')}
            {textwrap.indent(cls.render, '    ' * 3).lstrip(' ')}
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
        if cls.__name__ != '__yolo__component':
            cls.identifier = str(len(cls.registry))
            cls.registry[cls.identifier] = cls


class AppicationMeta(type):
    def __new__(mcls, name, bases, attrs):
        box = Box()
        class __yolo__component(BaseComponent, metaclass=ComponentMeta, app=box):
            registry = dict()

        attrs["_name"] = name
        attrs["component"] = __yolo__component
        ret = super(mcls, AppicationMeta).__new__(mcls, name, bases, attrs)
        box._set(ret)
        return ret


class BaseApplication:
    pass


class Application(BaseApplication, metaclass=AppicationMeta):
    router: "path" or "body" = "body"
    pyodide: bool = False
    pyodide_modules: list = []
    js_modules: list = []
    vdom: bool = False

    @classmethod
    def process(cls, data):
        return cls.component.process(data)

    @classmethod
    def code(cls):
        components = cls.component.registry.values()
        return ';\n'.join(c.build() for c in components)

    @classmethod
    def mount(cls, name):
        id = uuid.uuid4()
        return f'''
            <div id="{id}"></div>
            <script>YOLO_COMPONENTS["{name}"].render("{id}")</script>
        '''
