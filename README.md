### yoloboros
<p align="center">
  <img src="https://raw.githubusercontent.com/one-two-four-cee-four-one-plus/yoloboros/main/logo.webp" width="250" height="250"/>
</p>
<p align="center"><a href="https://yoloboros-47ceb119f8e0.herokuapp.com/">Demo</a></p>

`yoloboros` is a simple library for creating interactive webapps in python. It is framework agnostic and doesn't require any additional dependencies. `yoloboros` provides simple API for creating reusable components in python, generates HTML and js code for them and provides a unified way to communicate between components and server.
`yoloboros` can be plugged into any web framework, albeit being relatively straightforward with the structure and interaction with the server:
- No manual request/response handling
- No manual routing
- No manual serialization/deserialization
- No templating

`yolobors` is very similar to nagare, but with more expressive API and more flexibility (nagare requires stackless python and doesn't support python 3) and not specifically tailored for data apps like dash.

### Examples
##### Basic usage
Application is a container for components. Each application should have a root component.
```python
from yoloboros import Yoloboros


class App(Yoloboros):
    pass


class Root(App.root):
    def render(self):
        pass
```

###### Purely frontend-side component
Each component should have a render method, which returns a tree of HTML elements.
```python
class Root(App.root):
    def render(self):
        with button as btn:
            with btn.click as evt:
                console.log(evt)
            "Log to console"
```

###### Sever interaction
`fetch` method is called only once, when component is created. It makes a request to the server and returns a response. `render` method is called every time component is rendered.
```python
class Root(App.root):
    def fetch(self):
        from random import randint

        return {'number': randint(0, 100)}

    def render(self):
        with button as btn:
            with btn.click:
                console.log(self.state.number)
            "Log to console"
```

Ask for a number every time button is clicked. Here `yield` is used to separate server and client code.
```python
class Root(App.root):
    def render(self):
        with button as btn:
            with btn.click:
                request = yield {}

                from random import randint
                response = yield {'number': randint(0, 100)}

                console.log(response['number'])
            "Log to console"
```

###### Nested components
Components can be nested.
```python
class Value(App.component):
    def init(self):
        return {'value': None}

    def render(self):
        with div:
            f"Value: {self.state.value}<br>"


class Root(App.root):
    def render(self):
        with Value as val: pass

        with button as btn:
            with btn.click:
                request = yield {}

                from random import randint
                response = yield {'number': randint(0, 100)}

                val.state.value = response['number']
                val.render()
            'Generate random number'
```

### Integrations
##### Pyodide
You can use pyodide to run python code in the browser. `yoloboros` provides a simple way to use pyodide in your app. Note that pyodide is quite large and will increase your app size significantly. In addition the user is responsible for downloading pyodide and all the packages used in their app.
```python
class App(Yoloboros):
    pyodide = True


class Root(App.root):
    def init(self):
        return {'value': 0}

    def render(self):
        with div:
            f'Value: {self.state.value}'

        with button as btn:
            with btn.click:
                from random import randint
                self.state.value = randint(0, 100)
                self.render()
            'Generate random number'
```

### Installation
```bash
pip install yoloboros
```

### License
MIT