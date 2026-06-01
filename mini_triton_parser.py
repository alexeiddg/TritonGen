#!/usr/bin/env python3
"""
Mini-Triton Parser — Compilers Course Assignment
=================================================

CONTEXT-FREE GRAMMAR (EBNF)
----------------------------
program      ::= decorator kernel EOF
decorator    ::= '@' ID '.' ID
                 -- must be exactly @triton.jit
kernel       ::= 'def' ID '(' params ')' ':' '{' stmt_list '}'
params       ::= param (',' param)* | ε
param        ::= ID (':' ID '.' ID)?
                 -- optional type annotation, e.g. tl.constexpr
stmt_list    ::= stmt*
stmt         ::= assign | expr_stmt
                 -- lookahead: current=ID, next='=' → assign; else expr_stmt
assign       ::= ID '=' expr ';'
expr_stmt    ::= expr ';'
expr         ::= term (('+' | '-') term)*
term         ::= factor (('*' | '/') factor)*
factor       ::= NUMBER
               | '(' expr ')'
               | name_or_call
name_or_call ::= ID ('.' ID)? ('(' args ')')?
                 -- plain name, dotted name, call, or dotted call
args         ::= arg (',' arg)* | ε
arg          ::= expr
                 -- positional only; 'ID =' inside args is rejected (keyword arg)

TOKEN TYPES (produced by the lexer in this file)
-------------------------------------------------
AT  COLON  COMMA  DOT  EQUALS  LBRACE  LPAREN  MINUS  NUMBER
PLUS  RBRACE  RPAREN  SEMICOLON  SLASH  STAR  ID  EOF
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import Generator, List, Optional, Union

# ── Token type constants ───────────────────────────────────────────────────────

AT        = "AT"
COLON     = "COLON"
COMMA     = "COMMA"
DOT       = "DOT"
EQUALS    = "EQUALS"
LBRACE    = "LBRACE"
LPAREN    = "LPAREN"
MINUS     = "MINUS"
NUMBER    = "NUMBER"
PLUS      = "PLUS"
RBRACE    = "RBRACE"
RPAREN    = "RPAREN"
SEMICOLON = "SEMICOLON"
SLASH     = "SLASH"
STAR      = "STAR"
ID        = "ID"
EOF       = "EOF"

_DISPLAY = {
    AT: "@", COLON: ":", COMMA: ",", DOT: ".",
    EQUALS: "=", LBRACE: "{", LPAREN: "(",
    MINUS: "-", PLUS: "+", RBRACE: "}", RPAREN: ")",
    SEMICOLON: ";", SLASH: "/", STAR: "*",
    ID: "identificador", NUMBER: "número", EOF: "fin de archivo",
}


# ── Token dataclass ────────────────────────────────────────────────────────────

@dataclass
class Token:
    type: str
    value: str
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, {self.line}:{self.col})"


# ── Lexer ──────────────────────────────────────────────────────────────────────

_MASTER_RE = re.compile(
    r"(?P<SKIP>[ \t\r\n]+|#[^\n]*)"   # whitespace and line comments
    r"|(?P<NUMBER>\d+(?:\.\d+)?)"      # integer or float literal
    r"|(?P<ID>[A-Za-z_]\w*)"           # identifier
    r"|(?P<AT>@)"
    r"|(?P<DOT>\.)"
    r"|(?P<COLON>:)"
    r"|(?P<COMMA>,)"
    r"|(?P<SEMICOLON>;)"
    r"|(?P<LPAREN>\()"
    r"|(?P<RPAREN>\))"
    r"|(?P<LBRACE>\{)"
    r"|(?P<RBRACE>\})"
    r"|(?P<EQUALS>=)"
    r"|(?P<PLUS>\+)"
    r"|(?P<MINUS>-)"
    r"|(?P<STAR>\*)"
    r"|(?P<SLASH>/)"
    r"|(?P<MISMATCH>.)",
    re.DOTALL,
)


def tokenize(source: str) -> List[Token]:
    """Scan *source* and return a flat list of tokens ending with EOF."""
    tokens: List[Token] = []
    line = 1
    line_start = 0

    for m in _MASTER_RE.finditer(source):
        kind = m.lastgroup
        value = m.group()
        tok_start = m.start()
        col = tok_start - line_start + 1

        if kind == "SKIP":
            for i, ch in enumerate(value):
                if ch == "\n":
                    line += 1
                    line_start = tok_start + i + 1
            continue

        if kind == "MISMATCH":
            raise SyntaxError(
                f"INVALIDO: carácter inesperado {value!r} en línea {line}, col {col}"
            )

        tokens.append(Token(kind, value, line, col))

    tokens.append(Token(EOF, "", line, -1))
    return tokens


# ── AST node dataclasses ───────────────────────────────────────────────────────

@dataclass
class Number:
    value: str
    line: int = field(default=0, repr=False)

@dataclass
class Name:
    name: str
    line: int = field(default=0, repr=False)

@dataclass
class BinaryOp:
    op: str
    left: "Expr"
    right: "Expr"

@dataclass
class Call:
    callee: str
    args: List["Expr"]

@dataclass
class Param:
    name: str
    annotation: Optional[str] = None

@dataclass
class Assign:
    target: Name
    value: "Expr"

@dataclass
class ExprStmt:
    expr: "Expr"

@dataclass
class Kernel:
    name: str
    params: List[Param]
    body: List["Stmt"]

@dataclass
class Program:
    kernel: Kernel

Expr = Union[Number, Name, BinaryOp, Call]
Stmt = Union[Assign, ExprStmt]
ASTNode = Union[Program, Kernel, Param, Assign, ExprStmt, BinaryOp, Call, Name, Number]


# ── Parser ─────────────────────────────────────────────────────────────────────

class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    # ── Primitives ─────────────────────────────────────────────────────────────

    @property
    def _cur(self) -> Token:
        return self._tokens[self._pos]

    def _peek(self, offset: int = 1) -> Token:
        i = self._pos + offset
        return self._tokens[i] if i < len(self._tokens) else self._tokens[-1]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if tok.type != EOF:
            self._pos += 1
        return tok

    def _expect(self, type_: str) -> Token:
        tok = self._cur
        if tok.type != type_:
            got  = f"'{tok.value}'" if tok.value else _DISPLAY.get(tok.type, tok.type)
            want = _DISPLAY.get(type_, type_)
            raise ParseError(
                f"INVALIDO: esperaba '{want}' pero llegó {got} "
                f"en línea {tok.line}, col {tok.col}"
            )
        return self._advance()

    # ── Grammar rules ──────────────────────────────────────────────────────────

    def parseProgram(self) -> Program:
        self.parseDecorator()
        kernel = self.parseKernel()
        if self._cur.type != EOF:
            tok = self._cur
            raise ParseError(
                f"INVALIDO: tokens inesperados después del kernel '{tok.value}' "
                f"en línea {tok.line}, col {tok.col}"
            )
        return Program(kernel=kernel)

    def parseDecorator(self) -> None:
        if self._cur.type != AT:
            tok = self._cur
            got = f"'{tok.value}'" if tok.value else _DISPLAY.get(tok.type, tok.type)
            raise ParseError(
                f"INVALIDO: se esperaba el decorador '@triton.jit' pero llegó {got} "
                f"en línea {tok.line}, col {tok.col}"
            )
        self._advance()  # @
        tok = self._expect(ID)
        if tok.value != "triton":
            raise ParseError(
                f"INVALIDO: se esperaba '@triton.jit' pero llegó '@{tok.value}' "
                f"en línea {tok.line}, col {tok.col}"
            )
        self._expect(DOT)
        tok = self._expect(ID)
        if tok.value != "jit":
            raise ParseError(
                f"INVALIDO: se esperaba '@triton.jit' pero llegó '@triton.{tok.value}' "
                f"en línea {tok.line}, col {tok.col}"
            )

    def parseKernel(self) -> Kernel:
        tok = self._expect(ID)
        if tok.value != "def":
            raise ParseError(
                f"INVALIDO: se esperaba 'def' pero llegó '{tok.value}' "
                f"en línea {tok.line}, col {tok.col}"
            )
        name_tok = self._expect(ID)
        self._expect(LPAREN)
        params = self.parseParams()
        self._expect(RPAREN)
        self._expect(COLON)
        if self._cur.type != LBRACE:
            tok = self._cur
            got = f"'{tok.value}'" if tok.value else _DISPLAY.get(tok.type, tok.type)
            raise ParseError(
                f"INVALIDO: se esperaba '{{' para abrir el bloque del kernel pero llegó {got} "
                f"en línea {tok.line}, col {tok.col}"
            )
        self._advance()  # {
        body = self.parseStmtList()
        self._expect(RBRACE)
        return Kernel(name=name_tok.value, params=params, body=body)

    def parseParams(self) -> List[Param]:
        params: List[Param] = []
        if self._cur.type == RPAREN:
            return params
        params.append(self.parseParam())
        while self._cur.type == COMMA:
            self._advance()
            params.append(self.parseParam())
        return params

    def parseParam(self) -> Param:
        name_tok = self._expect(ID)
        annotation: Optional[str] = None
        if self._cur.type == COLON:
            self._advance()
            ns   = self._expect(ID)
            self._expect(DOT)
            attr = self._expect(ID)
            annotation = f"{ns.value}.{attr.value}"
        return Param(name=name_tok.value, annotation=annotation)

    def parseStmtList(self) -> List[Stmt]:
        stmts: List[Stmt] = []
        while self._cur.type not in (RBRACE, EOF):
            stmts.append(self.parseStmt())
        return stmts

    def parseStmt(self) -> Stmt:
        tok = self._cur
        # Reject unsupported control-flow keywords immediately
        _UNSUPPORTED = {"if", "while", "for", "return", "with", "import", "class", "try"}
        if tok.type == ID and tok.value in _UNSUPPORTED:
            raise ParseError(
                f"INVALIDO: instrucción '{tok.value}' fuera del alcance de Mini-Triton "
                f"en línea {tok.line}, col {tok.col}"
            )
        # Lookahead: ID followed by '=' → assignment statement
        if tok.type == ID and self._peek().type == EQUALS:
            return self.parseAssign()
        return self.parseExprStmt()

    def parseAssign(self) -> Assign:
        name_tok = self._advance()  # ID
        self._advance()             # =
        expr = self.parseExpr()
        self._expect(SEMICOLON)
        return Assign(
            target=Name(name=name_tok.value, line=name_tok.line),
            value=expr,
        )

    def parseExprStmt(self) -> ExprStmt:
        expr = self.parseExpr()
        self._expect(SEMICOLON)
        return ExprStmt(expr=expr)

    def parseExpr(self) -> Expr:
        left = self.parseTerm()
        while self._cur.type in (PLUS, MINUS):
            op    = self._advance().value
            right = self.parseTerm()
            left  = BinaryOp(op=op, left=left, right=right)
        return left

    def parseTerm(self) -> Expr:
        left = self.parseFactor()
        while self._cur.type in (STAR, SLASH):
            op    = self._advance().value
            right = self.parseFactor()
            left  = BinaryOp(op=op, left=left, right=right)
        return left

    def parseFactor(self) -> Expr:
        tok = self._cur
        if tok.type == NUMBER:
            self._advance()
            return Number(value=tok.value, line=tok.line)
        if tok.type == LPAREN:
            self._advance()
            expr = self.parseExpr()
            self._expect(RPAREN)
            return expr
        if tok.type == ID:
            return self.parseNameOrCall()
        got = f"'{tok.value}'" if tok.value else _DISPLAY.get(tok.type, tok.type)
        raise ParseError(
            f"INVALIDO: se esperaba una expresión pero llegó {got} "
            f"en línea {tok.line}, col {tok.col}"
        )

    def parseNameOrCall(self) -> Expr:
        tok    = self._advance()  # ID
        callee = tok.value

        # Optional: ID '.' ID  (e.g. tl.load, tl.arange)
        if self._cur.type == DOT:
            self._advance()
            attr   = self._expect(ID)
            callee = f"{callee}.{attr.value}"

        # Optional: '(' args ')'  — makes it a call
        if self._cur.type == LPAREN:
            self._advance()
            args = self.parseArgs()
            self._expect(RPAREN)
            return Call(callee=callee, args=args)

        return Name(name=callee, line=tok.line)

    def parseArgs(self) -> List[Expr]:
        args: List[Expr] = []
        if self._cur.type == RPAREN:
            return args
        self._reject_keyword_arg()
        args.append(self.parseExpr())
        while self._cur.type == COMMA:
            self._advance()
            self._reject_keyword_arg()
            args.append(self.parseExpr())
        return args

    def _reject_keyword_arg(self) -> None:
        """Raise immediately when a keyword arg pattern (ID '=') appears inside args."""
        if self._cur.type == ID and self._peek().type == EQUALS:
            tok = self._cur
            raise ParseError(
                f"INVALIDO: argumento con nombre '{tok.value}=...' no permitido "
                f"en línea {tok.line}, col {tok.col}"
            )


# ── AST pretty-printer ─────────────────────────────────────────────────────────

def _pp(
    node: ASTNode,
    prefix: str = "",
    is_last: bool = True,
) -> Generator[str, None, None]:
    b   = "└── " if is_last else "├── "
    ext = "    " if is_last else "│   "

    if isinstance(node, Program):
        yield "Program"
        yield from _pp(node.kernel, "", True)

    elif isinstance(node, Kernel):
        param_strs = [
            p.name + (f": {p.annotation}" if p.annotation else "")
            for p in node.params
        ]
        yield f'{prefix}{b}Kernel(name="{node.name}", params=[{", ".join(param_strs)}])'
        for i, stmt in enumerate(node.body):
            yield from _pp(stmt, prefix + ext, i == len(node.body) - 1)

    elif isinstance(node, Assign):
        yield f"{prefix}{b}Assign"
        yield from _pp(node.target, prefix + ext, False)
        yield from _pp(node.value,  prefix + ext, True)

    elif isinstance(node, ExprStmt):
        yield f"{prefix}{b}ExprStmt"
        yield from _pp(node.expr, prefix + ext, True)

    elif isinstance(node, BinaryOp):
        yield f'{prefix}{b}BinaryOp("{node.op}")'
        yield from _pp(node.left,  prefix + ext, False)
        yield from _pp(node.right, prefix + ext, True)

    elif isinstance(node, Call):
        if node.args:
            yield f'{prefix}{b}Call("{node.callee}")'
            for i, arg in enumerate(node.args):
                yield from _pp(arg, prefix + ext, i == len(node.args) - 1)
        else:
            yield f'{prefix}{b}Call("{node.callee}", args=[])'

    elif isinstance(node, Name):
        yield f'{prefix}{b}Name("{node.name}")'

    elif isinstance(node, Number):
        yield f'{prefix}{b}Number({node.value})'

    else:
        yield f"{prefix}{b}{node!r}"


def pretty_print(node: ASTNode) -> str:
    return "\n".join(_pp(node))


# ── CLI entrypoint ─────────────────────────────────────────────────────────────

def main() -> None:
    # Ensure UTF-8 output so tree glyphs render on all platforms
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    if len(sys.argv) != 2:
        print(f"Uso: python {sys.argv[0]} <archivo.tri>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print(f"INVALIDO: no se pudo abrir el archivo — {e}")
        sys.exit(1)

    try:
        tokens = tokenize(source)
    except SyntaxError as e:
        print(e)
        sys.exit(1)

    try:
        ast = Parser(tokens).parseProgram()
    except ParseError as e:
        print(e)
        sys.exit(1)

    print("VALIDO")
    print(pretty_print(ast))


if __name__ == "__main__":
    main()
