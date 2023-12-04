import ast
import string
import itertools
import sys
import textwrap
import functools

assert sys.version_info.major == 3
assert sys.version_info.minor == 10


class JsAST:
    _template = None
    _symbol = None
    _fields = ()

    def _render_field_value(self, f):
        ret = getattr(self, f)
        return ret.render() if isinstance(ret, JsAST) else str(ret)

    def get_mapping(self):
        return {f: self._render_field_value(f) for f in self._fields}

    def get_template(self):
        return string.Template(self._template)

    def render(self, indent=None):
        if self._symbol:
            return self._symbol
        else:
            return self.get_template().safe_substitute(self.get_mapping())


# class Jsmod(JsAST, ast.mod):
#     pass


class JsModule(JsAST, ast.Module):
    _fields = "body", "type_ignores"

    def render(self):
        return "\n".join(stmt.render() for stmt in self.body)


# class JsInteractive(JsAST, ast.Interactive):
#     _fields = 'body'

# class JsExpression(JsAST, ast.Expression):
#     _fields = 'body'

# class JsFunctionType(JsAST, ast.FunctionType):
#     _fields = 'argtypes', 'returns'

# class Jsstmt(JsAST, ast.stmt):
#     pass


class JsFunctionDef(JsAST, ast.FunctionDef):
    _fields = "name", "args", "body", "decorator_list", "returns", "type_comment"
    _template = """function $name($args) {
$body
};
    """

    def get_mapping(self):
        body = ";\n".join(f'{stmt.render().rstrip(";")}' for stmt in self.body) + ";"
        return {
            "name": self.name,
            "args": self.args.render(),
            "body": textwrap.indent(body, "    "),
        }


class MultilineLambda(JsAST, ast.AST):
    _fields = "args", "body"
    _template = """($args) => {
$body
}"""

    def get_mapping(self):
        body = ";\n".join(f'{stmt.render().rstrip(";")}' for stmt in self.body) + ";"
        return {
            "args": self.args.render(),
            "body": textwrap.indent(body, "    "),
        }


class JsAsyncFunctionDef(JsFunctionDef):
    _template = """
    const $name = async ($args) {
    $body
    }
    """


class JsClassDef(JsAST, ast.ClassDef):
    _fields = "name", "bases", "keywords", "body", "decorator_list"


class JsReturn(JsAST, ast.Return):
    _fields = ("value",)
    _template = "return $value;"


class JsDelete(JsAST, ast.Delete):
    _fields = ("targets",)

    def render(self):
        return "\n".join(f"delete {t.render()}" for t in self.targets)


class JsAssign(JsAST, ast.Assign):
    _fields = "targets", "value", "type_comment"

    def render(self):
        left = " = ".join(t.render() for t in self.targets)
        right = self.value.render()
        return f"{left} = {right};"


class JsAugAssign(JsAST, ast.AugAssign):
    _fields = "target", "op", "value"
    _template = "$target $op= $value"


# class JsAnnAssign(JsAST, ast.AnnAssign):
#     _fields = 'target', 'annotation', 'value', 'simple'


class JsFor(JsAST, ast.For):
    _fields = "target", "iter", "body", "orelse", "type_comment"
    _template = """
    $iter.forEach(($target) => {
    $body
    });
    """

    def get_mapping(self):
        return {
            "target": self.target.render(),
            "iter": self.iter.render(),
            "body": "\n".join(f"{stmt.render()}" for stmt in self.body),
        }


# class JsAsyncFor(JsAST, ast.AsyncFor):
#     _fields = 'target', 'iter', 'body', 'orelse', 'type_comment'


class JsWhile(JsAST, ast.While):
    _fields = "test", "body"  # , 'orelse'
    _template = """
    while ($test) {
    $body
    }'
    """


class JsIf(JsAST, ast.If):
    _fields = "test", "body", "orelse"
    _template = """
    if ($test) {
        $body
    }$orelse
    """

    def render(self):
        orelse = ""
        if self.orelse:
            orelse = (
                " else {\n"
                + "\n;".join(stmt.render() for stmt in self.orelse)
                + "\n}\n"
            )
        return self.get_template().safe_substitute(
            {
                "test": self.test.render(),
                "body": ";\n".join(part.render() for part in self.body),
                "orelse": orelse,
            }
        )


# class JsWith(JsAST, ast.With):
#     _fields = 'items', 'body', 'type_comment'


# class JsAsyncWith(JsAST, ast.AsyncWith):
#     _fields = 'items', 'body', 'type_comment'


# class JsMatch(JsAST, ast.Match):
#     _fields = 'subject', 'cases'


class JsRaise(JsAST, ast.Raise):
    _fields = ("exc",)  # 'cause'
    _template = "throw $exc;"


class JsTry(JsAST, ast.Try):
    _fields = "body", "handlers", "orelse", "finalbody"


class JsAssert(JsAST, ast.Assert):
    _fields = "test", "msg"
    _template = "assert($test, $msg);"


class JsImport(JsAST, ast.Import):
    _fields = ("names",)


class JsImportFrom(JsAST, ast.ImportFrom):
    _fields = "module", "names", "level"


# class JsGlobal(JsAST, ast.Global):
#     _fields = 'names',


# class JsNonlocal(JsAST, ast.Nonlocal):
#     _fields = 'names',


class JsExpr(JsAST, ast.Expr):
    _fields = ("value",)
    _template = "$value"


class JsPass(JsAST, ast.Pass):
    _template = ""


class JsBreak(JsAST, ast.Break):
    _template = "break;"


class JsContinue(JsAST, ast.Continue):
    _template = "continue;"


# class Jsexpr(JsAST, ast.expr):
#     pass


# class JsBoolOp(JsAST, ast.BoolOp):
#     _fields = 'op', 'values'


class JsNamedExpr(JsAST, ast.NamedExpr):
    _fields = "target", "value"
    _template = "$target = $value"


class JsBinOp(JsAST, ast.BinOp):
    _fields = "left", "op", "right"
    _template = "$left $op $right"


class JsUnaryOp(JsAST, ast.UnaryOp):
    _fields = "op", "operand"
    _template = "$op $operand"

    def get_mapping(self):
        return {
            "op": self.op._symbol,
            "operand": self.operand.render(),
        }


class JsLambda(JsAST, ast.Lambda):
    _fields = "args", "body"
    _template = "(($args) => ($body))"


class JsIfExp(JsAST, ast.IfExp):
    _fields = "test", "body", "orelse"
    _template = "(($test) ? ($body) : ($orelse))"


class JsDict(JsAST, ast.Dict):
    _fields = "keys", "values"

    def render(self):
        ret = []
        for k, v in zip(self.keys, self.values):
            ret.append(f"{k.render()}: {v.render()}")
        return "{" + ",".join(ret) + "}"


class JsSet(JsAST, ast.Set):
    _fields = ("elts",)


class JsListComp(JsAST, ast.ListComp):
    _fields = "elt", "generators"


class JsSetComp(JsAST, ast.SetComp):
    _fields = "elt", "generators"


class JsDictComp(JsAST, ast.DictComp):
    _fields = "key", "value", "generators"


class JsGeneratorExp(JsAST, ast.GeneratorExp):
    _fields = "elt", "generators"


class JsAwait(JsAST, ast.Await):
    _fields = ("value",)


class JsYield(JsAST, ast.Yield):
    _fields = ("value",)


class JsYieldFrom(JsAST, ast.YieldFrom):
    _fields = ("value",)


class JsCompare(JsAST, ast.Compare):
    _fields = "left", "ops", "comparators"

    def render(self):
        ops = [i.render() for i in self.ops]
        comparators = (i.render() for i in self.comparators)
        return functools.reduce(
            lambda left, pair: f"{left} {pair[0]} {pair[1]}",
            zip(ops, comparators),
            self.left.render(),
        )


class JsCall(JsAST, ast.Call):
    _fields = "func", "args", "keywords"

    def render(self):
        args = ", ".join(
            itertools.chain(
                (a.render() for a in self.args), (kw.render() for kw in self.keywords)
            )
        )
        return f"{self.func.render()}({args})"


class IIFE(JsCall):
    _fields = "func", "args", "keywords"

    def render(self):
        args = ", ".join(
            itertools.chain(
                (a.render() for a in self.args), (kw.render() for kw in self.keywords)
            )
        )
        return f"({self.func.render().strip()})({args.strip()})"


class JsFormattedValue(JsAST, ast.FormattedValue):
    _fields = "value", "conversion", "format_spec"

    def render(self):
        return self.value.render()


class JsJoinedStr(JsAST, ast.JoinedStr):
    _fields = ("values",)

    def render(self):
        value = ", ".join(v.render() for v in self.values)
        return "[" + value + '].join("")'


class JsConstant(JsAST, ast.Constant):
    _fields = "value", "kind"

    def render(self):
        if self.value is None:
            return "null"
        return f'"{self.value}"' if isinstance(self.value, str) else str(self.value)


class JsAttribute(JsAST, ast.Attribute):
    _fields = "value", "attr"  # , 'ctx'
    _template = "$value.$attr"


class JsSubscript(JsAST, ast.Subscript):
    _fields = "value", "slice"  # , 'ctx'
    _template = "$value[$slice]"


class JsStarred(JsAST, ast.Starred):
    _fields = ("value",)  # 'ctx'
    _template = "...$value"


class JsName(JsAST, ast.Name):
    _fields = ("id",)  # 'ctx'

    def render(self):
        return str(self.id)


class JsList(JsAST, ast.List):
    _fields = ("elts",)  # 'ctx'

    def render(self):
        elts = ", ".join(e.render() for e in self.elts)
        return f"[{elts}]"


class JsTuple(JsList):
    pass


class JsSlice(JsAST, ast.Slice):
    _fields = "lower", "upper", "step"


# class Jsexpr_context(JsAST, ast.expr_context):
#     pass

# class JsLoad(JsAST, ast.Load):
#     pass

# class JsStore(JsAST, ast.Store):
#     pass

# class JsDel(JsAST, ast.Del):
#     pass

# class Jsboolop(JsAST, ast.boolop):
#     pass


class JsAnd(JsAST, ast.And):
    pass


class JsOr(JsAST, ast.Or):
    pass


# class Jsoperator(JsAST, ast.operator):
#     pass


class JsAdd(JsAST, ast.Add):
    _symbol = "+"


class JsSub(JsAST, ast.Sub):
    _symbol = "-"


class JsMult(JsAST, ast.Mult):
    _symbol = "*"


# class JsMatMult(JsAST, ast.MatMult):
#     pass


class JsDiv(JsAST, ast.Div):
    _symbol = "/"


class JsMod(JsAST, ast.Mod):
    _symbol = "%"


# class JsPow(JsAST, ast.Pow):
#     pass


class JsLShift(JsAST, ast.LShift):
    _symbol = "<<"


class JsRShift(JsAST, ast.RShift):
    _symbol = ">>"


class JsBitOr(JsAST, ast.BitOr):
    _symbol = "|"


class JsBitXor(JsAST, ast.BitXor):
    _symbol = "^"


class JsBitAnd(JsAST, ast.BitAnd):
    _symbol = "&"


# class JsFloorDiv(JsAST, ast.FloorDiv):
#     pass

# class Jsunaryop(JsAST, ast.unaryop):
#     pass

# class JsInvert(JsAST, ast.Invert):
#     pass


class JsNot(JsAST, ast.Not):
    _symbol = "!"


class JsUAdd(JsAST, ast.UAdd):
    _symbol = "+"


class JsUSub(JsAST, ast.USub):
    _symbol = "-"


# class Jscmpop(JsAST, ast.cmpop):
#     pass


class JsEq(JsAST, ast.Eq):
    _template = "=="


class JsNotEq(JsAST, ast.NotEq):
    _template = "!="


class JsLt(JsAST, ast.Lt):
    _template = "<"


class JsLtE(JsAST, ast.LtE):
    pass


class JsGt(JsAST, ast.Gt):
    _template = ">"


class JsGtE(JsAST, ast.GtE):
    pass


class JsIs(JsAST, ast.Is):
    _template = "==="


class JsIsNot(JsAST, ast.IsNot):
    _template = "!=="


# class JsIn(JsAST, ast.In):
#     _fields =

# class JsNotIn(JsAST, ast.NotIn):
#     _fields =


class Jscomprehension(JsAST, ast.comprehension):
    _fields = "target", "iter", "ifs", "is_async"


# class Jsexcepthandler(JsAST, ast.excepthandler):
#     _fields =


class JsExceptHandler(JsAST, ast.ExceptHandler):
    _fields = "type", "name", "body"


class Jsarguments(JsAST, ast.arguments):
    _fields = (
        "posonlyargs",
        "args",
        "vararg",
        "kwonlyargs",
        "kw_defaults",
        "kwarg",
        "defaults",
    )

    def render(self):
        assert self.kwarg is None, self.kwarg.render()
        assert self.defaults == [], self.defaults
        args = [
            *(arg.render() for arg in itertools.chain(self.posonlyargs, self.args)),
            *(
                f"{k.render()}={v.render()}"
                for k, v in zip(self.kwonlyargs, self.kw_defaults)
            ),
        ]
        if self.vararg:
            args.append(f"...{self.vararg.render()}")
        if not args:
            return ""
        elif len(args) == 1:
            return args[0]
        else:
            return ", ".join(args)


class Jsarg(JsAST, ast.arg):
    _fields = "arg", "annotation", "type_comment"

    def render(self):
        return self.arg


class Jskeyword(JsAST, ast.keyword):
    _fields = "arg", "value"

    def render(self):
        return f"{self.arg}={self.value.render()}"


class Jsalias(JsAST, ast.alias):
    _fields = "name", "asname"


class Jswithitem(JsAST, ast.withitem):
    _fields = "context_expr", "optional_vars"


class Jsmatch_case(JsAST, ast.match_case):
    _fields = "pattern", "guard", "body"


# class Jspattern(JsAST, ast.pattern):
#     pass


class JsMatchValue(JsAST, ast.MatchValue):
    _fields = ("value",)


class JsMatchSingleton(JsAST, ast.MatchSingleton):
    _fields = ("value",)


class JsMatchSequence(JsAST, ast.MatchSequence):
    _fields = ("patterns",)


class JsMatchMapping(JsAST, ast.MatchMapping):
    _fields = "keys", "patterns", "rest"


class JsMatchClass(JsAST, ast.MatchClass):
    _fields = "cls", "patterns", "kwd_attrs", "kwd_patterns"


class JsMatchStar(JsAST, ast.MatchStar):
    _fields = ("name",)


class JsMatchAs(JsAST, ast.MatchAs):
    _fields = "pattern", "name"


class JsMatchOr(JsAST, ast.MatchOr):
    _fields = ("patterns",)


# class Jstype_ignore(JsAST, ast.type_ignore):
#     pass


class JsTypeIgnore(JsAST, ast.TypeIgnore):
    _fields = "lineno", "tag"


class JsNum(JsAST, ast.Num):
    _fields = ("n",)


class JsStr(JsAST, ast.Str):
    _fields = ("s",)


class JsBytes(JsAST, ast.Bytes):
    _fields = ("s",)


class JsNameConstant(JsAST, ast.NameConstant):
    _fields = "value", "kind"


# class JsEllipsis(JsAST, ast.Ellipsis):
#     pass

# class Jsslice(JsAST, ast.slice):
#     pass


class JsIndex(JsAST, ast.Index):
    pass


# class JsExtSlice(JsAST, ast.ExtSlice):
#     pass

# class JsSuite(JsAST, ast.Suite):
#     pass

# class JsAugLoad(JsAST, ast.AugLoad):
#     pass

# class JsAugStore(JsAST, ast.AugStore):
#     pass

# class JsParam(JsAST, ast.Param):
#     pass

TABLE = (
    # js type, py type
    (JsModule, ast.Module),
    (JsFunctionDef, ast.FunctionDef),
    (JsAsyncFunctionDef, ast.AsyncFunctionDef),
    (JsClassDef, ast.ClassDef),
    (JsReturn, ast.Return),
    (JsDelete, ast.Delete),
    (JsAssign, ast.Assign),
    (JsAugAssign, ast.AugAssign),
    (JsFor, ast.For),
    (JsWhile, ast.While),
    (JsIf, ast.If),
    (JsRaise, ast.Raise),
    (JsTry, ast.Try),
    (JsAssert, ast.Assert),
    (JsImport, ast.Import),
    (JsImportFrom, ast.ImportFrom),
    (JsExpr, ast.Expr),
    (JsPass, ast.Pass),
    (JsBreak, ast.Break),
    (JsContinue, ast.Continue),
    (JsBinOp, ast.BinOp),
    (JsUnaryOp, ast.UnaryOp),
    (JsLambda, ast.Lambda),
    (JsIfExp, ast.IfExp),
    (JsDict, ast.Dict),
    (JsSet, ast.Set),
    (JsListComp, ast.ListComp),
    (JsSetComp, ast.SetComp),
    (JsDictComp, ast.DictComp),
    (JsGeneratorExp, ast.GeneratorExp),
    (JsAwait, ast.Await),
    (JsYield, ast.Yield),
    (JsYieldFrom, ast.YieldFrom),
    (JsCompare, ast.Compare),
    (JsCall, ast.Call),
    (JsFormattedValue, ast.FormattedValue),
    (JsJoinedStr, ast.JoinedStr),
    (JsConstant, ast.Constant),
    (JsAttribute, ast.Attribute),
    (JsSubscript, ast.Subscript),
    (JsStarred, ast.Starred),
    (JsName, ast.Name),
    (JsList, ast.List),
    (JsTuple, ast.Tuple),
    (JsSlice, ast.Slice),
    (JsAnd, ast.And),
    (JsOr, ast.Or),
    (JsAdd, ast.Add),
    (JsSub, ast.Sub),
    (JsMult, ast.Mult),
    (JsDiv, ast.Div),
    (JsMod, ast.Mod),
    (JsLShift, ast.LShift),
    (JsRShift, ast.RShift),
    (JsBitOr, ast.BitOr),
    (JsBitXor, ast.BitXor),
    (JsBitAnd, ast.BitAnd),
    (JsNot, ast.Not),
    (JsEq, ast.Eq),
    (JsNotEq, ast.NotEq),
    (JsLt, ast.Lt),
    (JsLtE, ast.LtE),
    (JsGt, ast.Gt),
    (JsGtE, ast.GtE),
    (JsIs, ast.Is),
    (JsIsNot, ast.IsNot),
    (Jscomprehension, ast.comprehension),
    (JsExceptHandler, ast.ExceptHandler),
    (Jsarguments, ast.arguments),
    (Jsarg, ast.arg),
    (Jskeyword, ast.keyword),
    (Jsalias, ast.alias),
    (Jswithitem, ast.withitem),
    (Jsmatch_case, ast.match_case),
    (JsMatchValue, ast.MatchValue),
    (JsMatchSingleton, ast.MatchSingleton),
    (JsMatchSequence, ast.MatchSequence),
    (JsMatchMapping, ast.MatchMapping),
    (JsMatchClass, ast.MatchClass),
    (JsMatchStar, ast.MatchStar),
    (JsMatchAs, ast.MatchAs),
    (JsMatchOr, ast.MatchOr),
    (JsTypeIgnore, ast.TypeIgnore),
    (JsNum, ast.Num),
    (JsStr, ast.Str),
    (JsBytes, ast.Bytes),
    (JsNameConstant, ast.NameConstant),
    (JsIndex, ast.Index),
    (JsUAdd, ast.UAdd),
    (JsUSub, ast.USub),
)


class With(JsAST, ast.With):
    _fields = "items", "body", "type_comment"


class FormatContent(JsAST, ast.JoinedStr):
    _fields = ("values",)

    def render(self):
        values = list(
            f'"{value.value}"'
            if isinstance(value, JsConstant)
            else f"String({value.render()})"
            for value in self.values
        )
        if len(values) > 1:
            return "this._text([" + ", ".join(values) + '].join(""))'
        return f"this._text({values[0]})"


class FormatExprContent(JsAST, ast.FormattedValue):
    _fields = "value", "conversion", "format_spec"

    def render(self):
        return self.value.render()


class AssignAttribute(JsAST, ast.AnnAssign):
    _fields = "target", "annotation", "value", "simple"

    def render(self):
        return f'{self.target.id}.setAttribute("{self.annotation.id}", {self.value.render()})'
