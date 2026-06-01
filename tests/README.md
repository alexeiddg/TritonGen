# Tests — Mini-Triton Parser

## Cómo ejecutar

```bash
# Un archivo individual
python mini_triton_parser.py tests/valid_01.tri

# Todos los casos de una vez (bash/zsh)
for f in tests/*.tri; do
    echo -n "$f: "
    python mini_triton_parser.py "$f" | head -1
done
```

Salida en caso válido:

```
VALIDO
Program
└── Kernel(name="add", params=[x, y])
    └── Assign
        ├── Name("z")
        └── BinaryOp("+")
            ├── Name("x")
            └── Name("y")
```

Salida en caso inválido:

```
INVALIDO: argumento con nombre 'mask=...' no permitido en línea 2, col 26
```

## Tipos de token producidos por el lexer

| Tipo      | Patrón / carácter |
|-----------|-------------------|
| AT        | `@`               |
| COLON     | `:`               |
| COMMA     | `,`               |
| DOT       | `.`               |
| EQUALS    | `=`               |
| LBRACE    | `{`               |
| LPAREN    | `(`               |
| MINUS     | `-`               |
| NUMBER    | `\d+(\.\d+)?`    |
| PLUS      | `+`               |
| RBRACE    | `}`               |
| RPAREN    | `)`               |
| SEMICOLON | `;`               |
| SLASH     | `/`               |
| STAR      | `*`               |
| ID        | `[A-Za-z_]\w*`   |
| EOF       | (fin de entrada)  |

> `tl.load` se tokeniza como `ID("tl") DOT ID("load")`.  
> `def` y `jit` se tokenizen como `ID` y se validan por valor.

## Supuestos del lenguaje

- Un único kernel por archivo, precedido obligatoriamente por `@triton.jit`.
- Bloques delimitados por `{ }` (no por indentación).
- Toda instrucción termina con `;`.
- Solo hay asignaciones (`id = expr ;`) e instrucciones de expresión (`expr ;`).
- Las llamadas admiten argumentos posicionales únicamente; `name=value` es error.
- Los parámetros pueden llevar anotación `id : ns.attr` (p.ej. `BS: tl.constexpr`).
- Los comentarios de línea (`# ...`) son ignorados por el lexer.
- No se soporta: `if`, `while`, `for`, `return`, ni ninguna instrucción de control.
