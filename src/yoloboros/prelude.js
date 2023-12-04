class DomWrapper {
    constructor(element) {
        this.element = element;
    }

    setAttribute(name, value) {
        this.element.setAttribute(name, value);
    }

    setAction(component, name, ...args) {
        this.element.addEventListener('click', () => {
            component.actions[name](component, ...args);
        });
    }

    setCall(component, name, ...args) {
        this.element.addEventListener('click', () => {
            component.namespace[name](...args);
        });
    }
}

const __wrap = (element) => {
    return new DomWrapper(element);
};

const __create_element = (tag, attrs=null, parent=null, cb=null) => {
    const element = document.createElement(tag);
    if (attrs) {
        for (let key in attrs) {
            if ('style' === key) {
                for (let style_key in attrs[key]) {
                    element.style[style_key] = attrs[key][style_key];
                }
            } else if ('class' === key) {
                element.className = attrs[key];
            } else {
                element.setAttribute(key, attrs[key]);
            }
        }
    }
    if (cb) {
        cb(element);
    }
    if (parent) {
        parent.appendChild(element);
    }
    return element;
};

const __text = (element, text) => {
    if (element instanceof DomWrapper) {
        element = element.element;
    }

    if (!element.innerHTML) {
        element.innerHTML = '';
    }

    element.innerHTML += text;
};

class Component {
    constructor(identifier, init, render, actions) {
        this.identifier = identifier;
        this.init = init;
        this._render = render;
        this.actions = actions;
        this.namespace = {};

        this.state = this.init();
        this.domid = null;
        this.cid = crypto.randomUUID();
        REGISTRY[this.cid] = this;
    }

    render(domid=null) {
        if (domid) {
            this.domid = domid;
        }
        const element = document.getElementById(this.domid);
        element.innerHTML = '';
        this.namespace = {};
        this._render(this, element, this.action, this.call);
    }
}

const __make_component = (identifier, init, render, actions) => {
    return new Component(identifier, init, render, actions);
};

var REGISTRY = {
};

const __fetch = (identifier, action, request_json, callback, ...args) => {
    const request = new XMLHttpRequest();
    request.open('POST', `/`, true);
    request.setRequestHeader('Content-Type', 'application/json');
    request_data = request_json();
    if (args.length > 0) {
        request_data['args'] = args;
    }
    request.onload = () => {
        if (request.status >= 200 && request.status < 400) {
            callback(request_data, JSON.parse(request.responseText));
        } else {
            console.log('error');
        }
    };
    request.send(JSON.stringify({
        'identifier': identifier,
        'action': action,
        'request': request_data,
    }));
};
