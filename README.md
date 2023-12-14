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

### Frameworks integrations
WIP

### Example
```python
from yoloboros.client import Application


# Application is effecively a container for components
class App(Application):
    pass


class Counter(App.component):
    def init(self):
        return {"number": 0}

    def render(self):
        f"Number: {self.state.number}"

        with p:
            "Input value to add/substract"
            with input(id="number") as inp:
                pass

        with p, button as inc:
            inc: onclick = action("add", "+")
            "+"

        with p, button as dec:
            dec: onclick = action("add", "-")
            "-"

    def add(self):
        # this part is executed on client side
        value = parseInt(document.getElementById("number").value)
        request = yield {"value": value}  # yield request to the server
        print(request)  # print the request, this will be printed on server side
        response = yield {}  # yield response to the client
        # now client can process the response
        self.state.number += {"+": value, "-": -value}[request["args"][0]]
        self.render()
```

Generated JS will look like this:
```javascript
(() => {
    const identifier = "1";
    const actions = {};
    function init(self) {
        return {"number": 0};
    };

    function render(self, current=null) {
        __text(current, [__text(current, "Number: "), self.state.number].join(""));
        __create_element("p", null, current, (current) => {
            __text(current, "Input value to add/substract");
            __create_element("input", {"id": "number"}, current, (current) => {
                inp = __wrap(current);
                ;
            });
        });
        __create_element("p", null, current, (current) => {
            __create_element("button", null, current, (current) => {
                inc = __wrap(current);
                inc.setAction(self, "add", "+");
                __text(current, "+");
            });
        });
        __create_element("p", null, current, (current) => {
            __create_element("button", null, current, (current) => {
                dec = __wrap(current);
                dec.setAction(self, "add", "-");
                __text(current, "-");
            });
        });
    };

    function request_add(self, ...args) {
        __action = "add";
        function inner_request_add() {
            value = parseInt(document.getElementById("number").value);
            return {"value": value};
        };
            ;
        function receive_add(request, response) {
            self.state.number += {"+": value,"-": - value}[request["args"][0]];
            self.render();
        };
            ;
        return __fetch(identifier, __action, inner_request_add, receive_add, ...args);
    };

    actions["add"] = request_add;
    return __make_component(identifier, init, render, actions);
})();
```

### Installation
```bash
pip install yoloboros
```

### License
MIT