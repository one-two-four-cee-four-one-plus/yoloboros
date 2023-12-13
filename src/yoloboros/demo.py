# todo loop like youtube shorts
# ascii coins

from yoloboros.client import Application


class App(Application):
    pass


class Root(App.root):
    def init(self):
        return {'idx': 0}

    def render(self):
        with button as btn:
            with btn.click as evt:
                self.state.idx = self.state.idx - 1 if self.state.idx else 6
                self.render()
            'prev'

        with button as btn:
            with btn.click as evt:
                self.state.idx = (Math.abs(self.state.idx + 1) % 7)
                self.render()
            'next'

        if self.state.idx == 0:
            with p:
                'Welcome! This is a demo of https://github.com/one-two-four-cee-four-one-plus/yoloboros'
        if self.state.idx == 1:
            with p:
                'Root page<br>'
            with RootExample:pass
        elif self.state.idx == 2:
            with p:
                'Pure js'
            with PureJsExample:pass
        elif self.state.idx == 3:
            with p:
                'Basic server interactions'
            with summary, details, pre:
                '''
    class CoinFlipCounter(App.component):
        def init(self):
            return {"count": 0, "last": None, "total": 0}

        def render(self):
            with button as btn:
                btn: click = action('random_increment')
                'Flip a count and add result to counter'

            with div:
                f'{self.state.count}/{self.state.total}, {self.state.last}'

        def random_increment(self):
            request = yield {}

            from random import choice
            response = yield {"count": choice([0, 1])}

            self.state.count += response["count"]
            self.state.last = response["count"]
            self.state.total += 1
            self.render()
                '''

            with CoinFlipCounter:pass
        elif self.state.idx == 4:
            with p:
                'Code placement'
            with summary, details, pre:
                '''
    class CounterInline(App.component):
        def init(self):
            return {"count": 0, "last": None, "total": 0}

        def render(self):
            with button as btn:
                with btn.click:
                    request = yield {}

                    from random import choice
                    response = yield {"count": choice([0, 1])}

                    self.state.count += response["count"]
                    self.state.last = response["count"]
                    self.state.total += 1
                    self.render()

                'Flip a count and add result to counter'

            with div:
                f'{self.state.count}/{self.state.total}, {self.state.last}'
                '''
            with CounterInline:pass
        elif self.state.idx == 5:
            with p:
                'The benchmark'
            with summary, details, pre:
                '''
    from collections import deque
    from importlib import import_module


    class TodoList(App.component):
        db = deque(maxlen=20)
        uuid = import_module('uuid')

        def fetch(self):
            response = yield {'items': list(self.db)}

        def render(self):
            with input as inp: pass

            with button as btn:
                with btn.click:
                    request = yield {'text': inp.e.value}
                    item = {'text': request['text'], 'completed': False, 'id': str(self.uuid.uuid4())}
                    self.db.append(item)
                    response = yield item
                    self.state.items.push(response)
                    self.render()
                'Add'

            with ul:
                for item in self.state.items:
                    with li:
                        f'{item.text} {"+" if item.completed else "-"}  '
                        with button as btn:
                            with btn.click:
                                request = yield {'id': item.id}
                                item = next((i for i in self.db if i['id'] == request['id']))
                                item['completed'] = not item['completed']
                                response = yield item
                                Object.assign(self.state.items.find(lambda i: i.id == item.id), response)
                                self.render()

                            'Complete'

                        with button as btn:
                            with btn.click:
                                request = yield {'id': item.id}
                                item = next((pos for pos, i in enumerate(self.db) if i['id'] == request['id']))
                                del self.db[item]
                                response = yield request
                                idx = self.state.items.findIndex(lambda i: i.id == item.id)
                                self.state.items.splice(idx, 1)
                                self.render()
                            'Delete'
                '''
            with TodoList: pass
        elif self.state.idx == 6:
            with p:
                'The server'
            with Server: pass



class RootExample(App.component):
    def render(self):
        with pre:
            '''
    class Root(App.root):
        def init(self):
            return {'idx': 0}

        def render(self):
            with button as btn:
                with btn.click as evt:
                    self.state.idx = self.state.idx - 1 if self.state.idx else 6
                    self.render()
                'prev'

            with button as btn:
                with btn.click as evt:
                    self.state.idx = (Math.abs(self.state.idx + 1) % 7)
                    self.render()
                'next'

            if self.state.idx == 0:
                with p:
                    [welcome text]
            if self.state.idx == 1:
                with RootExample:pass
            elif self.state.idx == 2:
                with PureJsExample:pass
            elif self.state.idx == 3:
                with CoinFlipCounter:pass
            elif self.state.idx == 4:
                with CounterInline:pass
            elif self.state.idx == 5:
                with TodoList: pass
            elif self.state.idx == 6:
                with Server: pass
            '''


class PureJsExample(App.component):
    def render(self):
        with summary, details, pre:
            '''
    class PureJsExample(App.component):
        def render(self):
            with Greeter as grt:pass

            with label: 'Enter your name '
            with input as inp:
                with inp.input as evt:
                    grt.y.state.string = evt.target.value
                    grt.y.render()


    class Greeter(App.component):
        def init(self):
            return {"string": ""}

        def render(self):
            f'Hello, {self.state.string}!' if self.state.string else 'Hello!'
            '''
        with Greeter as grt:pass

        with label: 'Enter your name '
        with input as inp:
            with inp.input as evt:
                grt.y.state.string = evt.target.value
                grt.y.render()


class Greeter(App.component):
    def init(self):
        return {"string": ""}

    def render(self):
        f'Hello, {self.state.string}!' if self.state.string else 'Hello!'


class CoinFlipCounter(App.component):
    def init(self):
        return {"count": 0, "last": None, "total": 0}

    def render(self):
        with button as btn:
            btn: click = action('random_increment')
            'Flip a count and add result to counter'

        with div:
            f'{"¢".repeat(self.state.count)}<br>{"¢".repeat(self.state.total)}'

    def random_increment(self):
        request = yield {}

        from random import choice
        response = yield {"count": choice([0, 1])}

        self.state.count += response["count"]
        self.state.last = response["count"]
        self.state.total += 1
        self.render()


class CounterInline(App.component):
    def init(self):
        return {"count": 0, "last": None, "total": 0}

    def render(self):
        with button as btn:
            with btn.click:
                request = yield {}

                from random import choice
                response = yield {"count": choice([0, 1])}

                self.state.count += response["count"]
                self.state.last = response["count"]
                self.state.total += 1
                self.render()

            'Flip a count and add result to counter'

        with div:
            f'{"¢".repeat(self.state.count)}<br>{"¢".repeat(self.state.total)}'


from collections import deque
from importlib import import_module


class TodoList(App.component):
    db = deque(maxlen=20)
    uuid = import_module('uuid')

    def fetch(self):
        response = yield {'items': list(self.db)}

    def render(self):
        with input as inp: pass

        with button as btn:
            with btn.click:
                request = yield {'text': inp.e.value}
                item = {'text': request['text'], 'completed': False, 'id': str(self.uuid.uuid4())}
                self.db.append(item)
                response = yield item
                self.state.items.push(response)
                self.render()
            'Add'

        with ul:
            for item in self.state.items:
                with li:
                    f'{item.text} {"+" if item.completed else "-"}  '
                    with button as btn:
                        with btn.click:
                            request = yield {'id': item.id}
                            item = next((i for i in self.db if i['id'] == request['id']))
                            item['completed'] = not item['completed']
                            response = yield item
                            Object.assign(self.state.items.find(lambda i: i.id == item.id), response)
                            self.render()

                        'Complete'

                    with button as btn:
                        with btn.click:
                            request = yield {'id': item.id}
                            item = next((pos for pos, i in enumerate(self.db) if i['id'] == request['id']))
                            del self.db[item]
                            response = yield request
                            idx = self.state.items.findIndex(lambda i: i.id == item.id)
                            self.state.items.splice(idx, 1)
                            self.render()
                        'Delete'


class Server(App.component):
    def render(self):
        with summary, details, pre:
            '''
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import pathlib
    import json


    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            js = (pathlib.Path(__file__).parent / "prelude.js").read_text()
            self.wfile.write(
                f"""
                [script]{js}[/script]
                [script]{App.code}[/script]
                {App.mount()}
                """.encode()
            )

        def do_POST(self):
            length = int(self.headers["Content-Length"])
            request = json.loads(self.rfile.read(length))
            response = App.process(request)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())


    httpd = HTTPServer(("localhost", 3000), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

            '''


from http.server import BaseHTTPRequestHandler, HTTPServer
import pathlib
import json


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        js = (pathlib.Path(__file__).parent / "prelude.js").read_text()
        self.wfile.write(
            f"""
            <script>{js}</script>
            <script>{App.code}</script>
            {App.mount()}
            """.encode()
        )

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(length))
        response = App.process(request)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())


httpd = HTTPServer(("localhost", 3000), Handler)
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    pass
httpd.server_close()
