# Resultados esperados

| Archivo        | Resultado | Razón                                                              |
|----------------|-----------|--------------------------------------------------------------------|
| valid_01.tri   | VALIDO    | Kernel mínimo con asignación y suma binaria                        |
| valid_02.tri   | VALIDO    | Expresión con paréntesis y precedencia `*` sobre `+`              |
| valid_03.tri   | VALIDO    | Tres parámetros; verifica asociatividad `a + (b * c)`             |
| valid_04.tri   | VALIDO    | ExprStmt con llamada dotted `tl.load(x)`                          |
| valid_05.tri   | VALIDO    | Llamada normal con args mixtos: nombre, número y sub-expr         |
| valid_06.tri   | VALIDO    | Parámetro anotado `BS: tl.constexpr` y llamada `tl.arange`       |
| valid_07.tri   | VALIDO    | Kernel completo: pid, aritmética de offsets, load/store           |
| invalid_01.tri | INVALIDO  | Empieza con `def` — falta el decorador `@triton.jit`              |
| invalid_02.tri | INVALIDO  | Bloque sin `{` — el parser espera `{` después de `:`             |
| invalid_03.tri | INVALIDO  | Instrucción sin `;` — el parser espera `;` antes de `}`           |
| invalid_04.tri | INVALIDO  | `z = x + ;` — el operando derecho está vacío (token inesperado)   |
| invalid_05.tri | INVALIDO  | `mask=1` dentro de args — keyword arg explícitamente rechazado    |
| invalid_06.tri | INVALIDO  | `if` no forma parte del lenguaje Mini-Triton                       |
