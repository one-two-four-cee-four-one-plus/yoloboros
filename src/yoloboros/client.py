import ast
import inspect
import textwrap

from yoloboros.transformer import JsTranslator, NodeRenderer, ActionRenderer


class ComponentMeta(type):
    def __new__(mcls, name, bases, attrs):
        attrs["requests"] = dict()
        attrs["responses"] = dict()

        if render := attrs.get("render"):
            render = ast.fix_missing_locations(NodeRenderer(render).walk())
            attrs["render"] = JsTranslator(render).walk().render()

        if init := attrs.get("init"):
            attrs["init"] = textwrap.dedent(JsTranslator(init).walk().render())

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
    const identifier = "{cls.identifier}";
    const actions = {{}};
{textwrap.indent(cls.init, '    ')}
{textwrap.indent(cls.render, '    ')}
"""
        )
        for k, v in cls.requests.items():
            ret += textwrap.indent(v, "    ") + "\n"
            ret += f'    actions["{k}"] = request_{k};\n'

        ret += "    return __make_component(identifier, init, render, actions);\n})();"
        return ret

    def __init_subclass__(cls):
        cls.identifier = str(len(cls.registry))
        cls.registry[cls.identifier] = cls


class AppicationMeta(type):
    def __new__(mcls, name, bases, attrs):
        class component(BaseComponent, metaclass=ComponentMeta):
            registry = dict()

        attrs["component"] = component
        return super(mcls, AppicationMeta).__new__(mcls, name, bases, attrs)


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
