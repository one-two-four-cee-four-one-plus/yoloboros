from yoloboros.client import Application


class App(Application):
    pass


class Root(App.component):
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
        value = parseInt(document.getElementById("number").value)
        request = yield {"value": value}
        response = yield {}
        self.state.number += {"+": value, "-": -value}[request["args"][0]]
        self.render()


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
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            </head>
            <body>
            <div id="root"></div>
            <script>
            {js}
            const __root = {Root.build()};
            __root.render('root');
            </script>
            </body>
            </html>
            """.encode()
        )

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        data = json.loads(self.rfile.read(length))
        response = App.process(data)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())


httpd = HTTPServer(("localhost", 3000), Handler)
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    pass
httpd.server_close()
