class YoloWrapper {
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

const __yolo__wrap = (element) => {
    return new YoloWrapper(element);
};

const __yolo__create_element = (tag, attrs=null, parent=null, cb=null) => {
    let element = null
    let yolo_elem = tag.startsWith('yolo:');
    if (yolo_elem) {
        element = document.createElement('div');
        element.setAttribute('id', crypto.randomUUID());
    } else {
        element = document.createElement(tag);
    }
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
    if (yolo_elem) {
        YOLO_COMPONENTS[tag.substr(5)].render(element)
    }
    if (cb) {
        cb(element);
    }
    if (parent) {
        parent.appendChild(element);
    }
    return element;
};

const __yolo__text = (element, text) => {
    if (element instanceof YoloWrapper) {
        element = element.element;
    }

    if (!element.innerHTML) {
        element.innerHTML = '';
    }

    element.innerHTML += text;
};

class YoloComponent {
    constructor(identifier, init, render, actions) {
        this.identifier = identifier;
        this.init = init;
        this._render = render;
        this.actions = actions;
        this.namespace = {};

        this.state = this.init();
        this.domid = null;
        this.cid = crypto.randomUUID();
        YOLO_REGISTRY[this.cid] = this;
    }

    render(domid_or_element=null) {
        if (typeof domid_or_element == 'string') {
            this.domid = domid_or_element;
            const element = document.getElementById(this.domid);
            element.innerHTML = '';
            this.namespace = {};
            this._render(this, element, this.action, this.call);
        } else if (domid_or_element instanceof Node) {
            domid_or_element.innerHTML = '';
            this.namespace = {};
            this._render(this, domid_or_element, this.action, this.call);
        }
    }
}

const __yolo__make_component = (identifier, init, render, actions) => {
    return new YoloComponent(identifier, init, render, actions);
};

var YOLO_REGISTRY = {};
var YOLO_COMPONENTS = {};

const __yolo__fetch = (identifier, action, request_json, callback, ...args) => {
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
