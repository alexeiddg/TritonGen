# TritonGen — Onboarding Completo

> **A quién va dirigido:** cualquier persona que llega al repo sin contexto previo (investigador, colaborador, revisión de código, o el propio autor volviendo después de meses). Este doc te lleva de cero a entender qué hace el sistema, por qué está diseñado así, y cómo verificar que cada parte funciona.

---

## Tabla de contenidos

1. [¿Qué es TritonGen?](#1-qué-es-tritongen)
2. [Motivación e hipótesis de investigación](#2-motivación-e-hipótesis-de-investigación)
3. [Arquitectura general](#3-arquitectura-general)
4. [Módulos en profundidad](#4-módulos-en-profundidad)
   - [shared/](#41-shared--infraestructura-compartida)
   - [cluster1/](#42-cluster1--generación-con-gramática)
   - [cluster2/](#43-cluster2--repair-loop-de-correctness)
   - [cluster3/](#44-cluster3-diferido)
5. [Flujo de datos de extremo a extremo](#5-flujo-de-datos-de-extremo-a-extremo)
6. [Formato de datos: EvalResult](#6-formato-de-datos-evalresult)
7. [Infraestructura Modal](#7-infraestructura-modal)
8. [Taxonomía de fallos y niveles de evaluación](#8-taxonomía-de-fallos-y-niveles-de-evaluación)
9. [Análisis estadístico factorial](#9-análisis-estadístico-factorial)
10. [Cómo correr el proyecto](#10-cómo-correr-el-proyecto)
11. [Tests manuales explicados](#11-tests-manuales-explicados)
12. [Preguntas frecuentes / trampas comunes](#12-preguntas-frecuentes--trampas-comunes)
13. [Glosario](#13-glosario)
14. [Mapa de docs existentes](#14-mapa-de-docs-existentes)

---

## 1. ¿Qué es TritonGen?

TritonGen es un framework de **experimentación científica** que estudia cómo distintos mecanismos de control mejoran la calidad de kernels GPU escritos en [Triton](https://triton-lang.org/) generados por un LLM.

En términos concretos:

> Dado un LLM (ej. Llama-3 / CodeLlama), ¿cuánto mejora la probabilidad de que genere un kernel Triton correcto y eficiente si aplicamos:
> - **Gramática guiada** (restringir tokens durante el decode para que el código sea sintácticamente válido)
> - **Bucle de reparación** (dar feedback de errores al modelo y pedirle que lo corrija)
> - **Feedback de rendimiento** (dar al modelo métricas de speedup y pedirle que optimice)?

El experimento está estructurado como un **diseño factorial 2³** (tres factores binarios: G, C, P) que prueba las 8 combinaciones posibles. Actualmente solo las primeras 4 (2²: sin nada, G, C, G+C) están completas.

**¿Por qué importa?** Triton es el lenguaje de bajo nivel que usa PyTorch para kernels personalizados. Escribirlos bien es difícil: requiere conocimiento de memoria GPU, acceso a registros, warp-level synchronization. Si los LLMs pudieran generar kernels correctos y rápidos de manera confiable, se aceleraría enormemente la investigación en ML.

---

## 2. Motivación e hipótesis de investigación

### El problema

Los LLMs generan código que compila a veces, pero que es correcto numéricamente mucho menos frecuentemente, y que es eficiente todavía menos. Para Triton específicamente:

- Errores de parseo (el código no es Python válido)
- Errores de compilación (Triton no acepta la semántica del kernel)
- Errores numéricos (produce resultados incorrectos para algunos shapes/dtypes)
- Errores de rendimiento (funciona pero es más lento que PyTorch eager)

### Las tres palancas (factores)

| Factor | Nombre | Qué hace | Nivel "ON" |
|--------|--------|----------|------------|
| **G** | Grammar | Decodificación gramatical con xgrammar + GBNF | Tokenes restringidos a código Triton válido |
| **C** | Correctness | Repair loop: LLM recibe errores y lo intenta de nuevo | Hasta 5 intentos de reparación por kernel |
| **P** | Performance | Feedback de speedup | (Diferido — Cluster 3) |

### Hipótesis principal

> Aplicar G+C conjuntamente produce una tasa de correctness numéricamente superior a la suma de G solo y C solo (efecto de interacción positivo).

---

## 3. Arquitectura general

```
TritonGen/
│
├── cluster1/          ← FACTOR G: generación con gramática, evaluación L0-L1
│   ├── generation/    ← constrained_gen.py (gramática on/off)
│   ├── grammar/       ← archivos .gbnf + validador Lark
│   ├── constraints/   ← hardware_checker (budget de memoria)
│   ├── data/          ← specs de kernels (relu, softmax, matmul)
│   ├── validation/    ← compile_check.py
│   ├── experiments/   ← run_cluster1.py (entry point)
│   └── tests/
│
├── cluster2/          ← FACTOR C: repair loop, evaluación L2 (correctness)
│   ├── feedback/      ← repair_loop.py + prompts.py
│   ├── generation/    ← modal generation C2
│   ├── replay/        ← reproduce artefactos de C1 para condiciones none/G
│   ├── experiments/   ← run_cluster2_modal.py (entry point)
│   └── tests/
│
├── cluster3/          ← FACTOR P: diferido, sin implementar
│
├── shared/            ← INFRAESTRUCTURA COMPARTIDA
│   ├── eval/          ← pipeline de evaluación, schema, niveles, fallos
│   ├── modal_harness/ ← RemoteGenerator (LLM en GPU remota via Modal)
│   ├── analysis/      ← factorial.py (estadísticas)
│   ├── factors/       ← cells.py (normalización G/C/P)
│   └── configs/
│
├── outputs/           ← Artefactos JSONL (resultados reales)
│   ├── cluster1/      ← none_n20.jsonl, g_n20.jsonl
│   └── cluster2/      ← c_n20.jsonl, g_plus_c_n20.jsonl
│
├── docs/              ← Documentación citation-grade
├── audits/            ← Registros de verificación históricos
└── .contracts/        ← Scope formal del proyecto
```

### Principios de diseño

**1. Separación estricta de dependencias pesadas**
El `shared/modal_harness/` tiene una regla explícita: no importar `torch`, `triton`, ni `xgrammar` a nivel de módulo. Solo se importan dentro de las clases Modal que se ejecutan remotamente. Esto garantiza que el código de orquestación local no necesita un entorno GPU.

**2. Artefactos inmutables como JSONL**
Los resultados se escriben una vez en archivos `.jsonl` (una fila JSON por línea). Nunca se modifican los artefactos existentes; si hay un run nuevo, se escribe un archivo nuevo. Esto permite reproducibilidad y auditoría.

**3. EvalResult como contrato de datos**
Toda salida del sistema es un `EvalResult` — un dataclass Python con ~90 campos documentados. Las claves ausentes son `None`, no se omiten. Esto garantiza que el análisis estadístico siempre trabaja con el mismo esquema.

**4. Capas de evaluación independientes**
Las evaluaciones son **pipelines con niveles** (L0 → L1 → L2 → L3 → L4). Un kernel que falla en L1 (compile) nunca se evalúa en L2 (correctness). Esto permite análisis por nivel de fallo sin contaminar métricas de niveles superiores.

---

## 4. Módulos en profundidad

### 4.1 `shared/` — Infraestructura compartida

#### `shared/eval/schema.py` — El corazón del sistema

Define `EvalResult`, el dataclass que representa **un intento de generar un kernel**.

```
kernel_id + sample_index + condition → EvalResult
```

Cada fila JSONL es un EvalResult serializado. Los campos se agrupan en:
- **Identidad**: `kernel_id`, `kernel_class`, `condition`, `sample_index`
- **Fuente**: `source` (código generado), `source_hash`, `ast_hash`
- **Nivel alcanzado**: `level_reached` (0, 1, 2, 3, 4)
- **Por nivel**: campos `parse_*`, `compile_*`, `functional_*`, `safe_*`, `perf_*`
- **Gramática**: `grammar_active`, `grammar_variant`, `grammar_sha`
- **Reparación**: `repair_iteration`, `repair_budget`, `repair_converged`, `repair_traces`
- **Provenance**: hashes de modelo, tokenizer, imagen Modal

**Por qué importa**: cualquier análisis estadístico downstream solo necesita leer JSONL y filtrar por `condition`. El schema es estable — cambiar un nombre de campo invalida todos los artefactos existentes, de ahí la política de `model_revision` e `image_sha` inmutables.

#### `shared/eval/pipeline.py` — El secuenciador de evaluación

Orquesta el pipeline L0 → L1 → L2 → L3 → L4 en orden. Cada nivel es un módulo pluggable en `shared/eval/levels/`:

```
parse (L0) → compile (L1) → correctness (L2) → sanitizer (L3) → performance (L4)
```

Si un nivel falla, el pipeline para y asigna el `failure_code` correspondiente. La razón de este diseño: compilar un kernel que no parsea es imposible; evaluar correctness de un kernel que no compila no tiene sentido.

#### `shared/eval/failure_taxonomy.py` — Códigos de fallo canónicos

Define la taxonomía de errores con códigos normalizados:

| Código | Nivel | Causa |
|--------|-------|-------|
| `F0_PARSE` | L0 | SyntaxError en Python o AST inválido |
| `F1_COMPILE` | L1 | Triton rechaza el kernel (semántica inválida) |
| `F2_NUMERIC_LARGE` | L2 | Error numérico grande (max_rel_diff > threshold) |
| `F2_TIMEOUT` | L2 | El kernel excede el tiempo límite |
| `F2_RUNTIME` | L2 | Runtime error durante ejecución |
| `F3_UB` | L3 | Comportamiento indefinido detectado |

**Por qué importa**: permite análisis de "dónde falla" sin depender de strings de error libres, que varían entre versiones de Triton.

#### `shared/modal_harness/generation.py` — El generador remoto

Clase Modal `RemoteGenerator` que:
1. Carga el modelo LLM en una GPU remota (L4 o L40S)
2. Acepta un prompt + opciones de gramática
3. Ejecuta `model.generate()` con o sin `TritonGrammarLogitsProcessor`
4. Retorna el código generado + metadata de provenance

La razón de la capa Modal: los modelos LLM necesitan GPU para inferencia. Modal permite ejecutar en GPU en la nube sin gestionar servidores. El código de orquestación local (que decide qué kernels generar) no necesita GPU.

#### `shared/analysis/factorial.py` — Estadísticas del experimento

Implementa el análisis factorial 2² / 2³:
- **Regresión logística**: estima el efecto de cada factor (G, C) sobre `pass@1`
- **Bootstrap CI**: intervalos de confianza con remuestreo (no asume normalidad)
- **Efecto de interacción**: ¿G+C > G + C - none? (hipótesis principal)

---

### 4.2 `cluster1/` — Generación con gramática

#### ¿Qué hace Cluster 1?

Genera kernels para 3 clases de operaciones GPU bajo 2 condiciones:
- **none**: generación libre (el LLM escribe lo que quiera)
- **G**: generación guiada por gramática (tokens restringidos al subconjunto Triton válido)

Evalúa hasta **L1** (compilación). No evalúa correctness aquí.

#### `cluster1/generation/constrained_gen.py` — Entry point de generación

Función `generate_source(prompt, grammar_active, grammar_variant, ...)`:

```python
# Con gramática ON:
processor = TritonGrammarLogitsProcessor(grammar)
output = model.generate(..., logits_processor=[processor])

# Con gramática OFF:
output = model.generate(...)  # sin restricciones
```

Retorna un `DecodedKernel` con: código generado, tasa de tokens enmascarados, stop reason, hash de gramática.

**Por qué la tasa de tokens enmascarados importa**: si la gramática enmascara >80% de los tokens en ciertos pasos, puede estar "forzando" código incorrecto. Esta métrica es un proxy de cuánta restricción está imponiendo la gramática.

#### `cluster1/grammar/triton_kernel_agnostic.gbnf` — La gramática

Archivo en formato GBNF (variante de BNF para llama.cpp / xgrammar) que define la sintaxis válida de un kernel Triton. El archivo "agnostic" es task-agnostic — no asume qué operación realiza el kernel, solo que sigue la estructura Triton.

xgrammar compila este archivo a un autómata finito que puede evaluar, para cada posición en el vocabulario del tokenizer, si agregar ese token mantiene el texto en el lenguaje definido por la gramática.

#### `cluster1/data/kernels/` — Especificaciones de kernels

Tres clases de kernels con spec formal:

| Clase | Operación | Referencia eager |
|-------|-----------|-----------------|
| `elementwise_relu` | ReLU element-wise | `torch.relu()` |
| `reduction_softmax` | Softmax por filas | `torch.softmax(..., dim=-1)` |
| `matmul_tiled_gemm` | Multiplicación matricial tileada | `torch.matmul()` |

Cada spec define: nombre, clase, launcher (cómo llamar al kernel), compile spec, shapes de test, dataset de dtype.

---

### 4.3 `cluster2/` — Repair loop de correctness

#### ¿Qué hace Cluster 2?

Toma los kernels que fallaron en L1 o pasa a evaluar L2 (correctness numérica) bajo 2 condiciones:
- **C**: sin gramática, con bucle de reparación
- **G+C**: con gramática, con bucle de reparación

Para las condiciones **none** y **G** (sin reparación), reproduce los artefactos de Cluster 1 ("replay").

#### `cluster2/feedback/repair_loop.py` — El bucle de reparación

```
attempt 0: generar kernel inicial
  ↓ evaluar L2
  ↓ si falla: generar feedback (prompts.py)
attempt 1: regenerar con feedback de intento 0
  ↓ evaluar L2
  ↓ si falla: generar feedback
...
attempt N (budget=5): último intento
  ↓ marcar repair_converged=False si sigue fallando
```

Cada intento queda registrado en `repair_traces` — una lista de `RepairTrace` que captura: código generado, nivel alcanzado, failure_code, feedback enviado.

**Por qué budget=5**: equilibrio entre costo de inferencia y utilidad marginal de cada intento adicional (empíricamente, la mayoría de reparaciones exitosas ocurren en los primeros 2-3 intentos).

#### `cluster2/feedback/prompts.py` — Prompts de feedback

Para cada `failure_code`, construye un prompt específico. Por ejemplo:
- `F1_COMPILE`: incluye el mensaje de error de Triton + instrucciones de cómo corregir errores comunes de compilación Triton
- `F2_NUMERIC_LARGE`: incluye el `max_rel_diff`, el shape que falló, y sugerencias de corrección numérica

La especificidad del feedback es clave: un prompt genérico de "tienes un error" es mucho menos útil que "en el shape [1024, 1024], dtype=float16, tu kernel produce valores con error relativo 0.34 en la posición [512, 0]. Verifica la reducción de precisión en la acumulación."

---

### 4.4 `cluster3/` — Diferido

No implementado aún. Añadirá el factor P (performance feedback). El design está en `docs/10_cluster3_drift_prevention_plan.md`.

---

## 5. Flujo de datos de extremo a extremo

```
[Cluster 1]

Kernel Spec (relu/softmax/matmul)
    │
    ▼
Prompt Builder
    │
    ▼
RemoteGenerator (Modal GPU)
    ├── grammar OFF → código libre
    └── grammar ON  → código restringido (xgrammar)
    │
    ▼
EvalPipeline
    ├── L0: ¿parsea como Python válido?
    └── L1: ¿compila con Triton?
    │
    ▼
EvalResult → outputs/cluster1/*.jsonl


[Cluster 2]

EvalResult de Cluster 1 (condiciones none, G) → replay directo
    │
    ▼ (condiciones C, G+C)
RepairLoop (budget=5)
    ├── attempt 0: generar
    │       ↓ L2: ¿correcto numéricamente?
    │       ↓ si falla → feedback
    ├── attempt 1: reparar con feedback
    │       ↓ L2
    │       ...
    └── attempt N → EvalResult con repair_traces
    │
    ▼
outputs/cluster2/*.jsonl


[Análisis]

JSONL (none, G, C, G+C)
    │
    ▼
Aggregation (pass@k, failure distribution)
    │
    ▼
Factorial Analysis (logistic regression, bootstrap CI)
    │
    ▼
outputs/analysis/factorial_2x2_preliminary.json
```

---

## 6. Formato de datos: EvalResult

Cada fila de los archivos JSONL es un JSON que representa un `EvalResult`. Aquí un ejemplo real simplificado:

```json
{
  "kernel_id": "elementwise_relu_none_s0",
  "kernel_name": "elementwise_relu",
  "kernel_class": "elementwise",
  "condition": "none",
  "sample_index": 0,
  "model_id": "codellama/CodeLlama-13b-hf",
  "run_id": "run_2024_cluster1_none",
  "timestamp": "2024-01-15T10:23:45Z",
  "source": "import triton\n@triton.jit\ndef kernel(x_ptr, y_ptr, n, BLOCK: tl.constexpr):\n    ...",
  "source_hash": "sha256:abc123...",
  "ast_hash": "sha256:def456...",
  "level_reached": 1,
  "parse_success": true,
  "parse_error": null,
  "has_triton_decorator": true,
  "signature_valid": true,
  "compile_success": true,
  "compile_error": null,
  "failure_code": null,
  "grammar_active": false,
  "grammar_variant": null,
  "functional_success": null,
  "repair_iteration": null,
  "repair_converged": null
}
```

**Regla importante**: un campo `null` significa "no evaluado", no "falló". Un campo `false` significa "evaluado y falló". Esta distinción es crítica para el análisis.

---

## 7. Infraestructura Modal

[Modal](https://modal.com) es la plataforma que permite ejecutar código Python en GPUs en la nube sin gestionar servidores.

### Cómo funciona

```python
# Local: este código corre en tu laptop
generator = RemoteGenerator()

# Remoto: este método corre en una GPU L4 en Modal
result = generator.generate.remote(request)
```

### Clases Modal principales

| Clase | Archivo | GPU | Propósito |
|-------|---------|-----|-----------|
| `RemoteGenerator` | `shared/modal_harness/generation.py` | L40S | Inferencia LLM + gramática |
| `CompileRunner` | `shared/modal_harness/compile_runner.py` | L4 | Compilación Triton |
| `C2Generator` | `cluster2/generation/generation.py` | L40S | Generación C2 con repair context |

### Por qué Modal y no Colab/AWS directamente

1. **Cold start predecible**: las imágenes Modal se construyen una vez y se reusan — el `modal_image_sha` en cada `EvalResult` garantiza que todos los rows de un run usaron el mismo entorno
2. **Paralelismo trivial**: `.map()` distribuye automáticamente sobre múltiples GPUs
3. **Sin gestión de estado**: si falla un worker, Modal lo reintenta automáticamente

### Secrets y configuración

Las credenciales (HuggingFace token para descargar modelos, etc.) se definen en `shared/modal_harness/secrets.py` como `modal.Secret`. Nunca están en el código.

---

## 8. Taxonomía de fallos y niveles de evaluación

### Niveles de evaluación

```
L0: Parse
    ¿Es Python sintácticamente válido?
    ¿Tiene @triton.jit decorator?
    ¿La firma del kernel es correcta?

L1: Compile
    ¿Triton puede compilar el kernel?
    (Requiere GPU — se hace en Modal)

L2: Correctness
    Para cada (shape, dtype) en el test set:
        resultado_kernel vs resultado_eager (torch)
        max_abs_diff y max_rel_diff deben estar bajo threshold

L3: Sanitizer (safety)
    ¿Accesos fuera de bounds?
    ¿Comportamiento indefinido detectado por análisis simbólico?

L4: Performance
    kernel_time_ms vs eager_time_ms
    speedup_vs_eager, speedup_vs_compile
```

### Cómo interpretar `level_reached`

- `level_reached = 0`: falló en parse (L0)
- `level_reached = 1`: pasó parse, falló en compile (L1) O pasó compile y no se evaluó más
- `level_reached = 2`: llegó a correctness

### Métricas clave

| Métrica | Definición | Nivel |
|---------|-----------|-------|
| `compile@1` | P(compila en 1 intento) | L1 |
| `pass@1` | P(pasa correctness en 1 intento) | L2 |
| `pass@k` | P(al menos 1 de k muestras pasa) | L2 |
| `repair_convergence_rate` | P(repair loop converge antes de budget) | L2+C |

---

## 9. Análisis estadístico factorial

### Diseño 2² (actual)

| | G=0 | G=1 |
|-|-----|-----|
| **C=0** | none (baseline) | G |
| **C=1** | C | G+C |

### Métricas que se computan

1. **pass@1 por celda**: tasa de éxito en primer intento
2. **Odds ratio**: efecto de cada factor sobre log-odds de pasar
3. **Efecto de interacción**: `OR(G+C) / (OR(G) * OR(C))` — si > 1, hay sinergia
4. **Bootstrap 95% CI**: intervalo de confianza via remuestreo (5000 iteraciones)

### ¿Por qué bootstrap y no t-test?

Los outcomes son binarios (pasa/falla), la distribución no es normal, y el n es pequeño (20 muestras × 3 kernels = 60 por celda). Bootstrap es más robusto en este régimen.

### Estado actual de los resultados

Los resultados están en `outputs/analysis/factorial_2x2_preliminary.json` pero tienen `metadata.reportable = false`. Esto significa que **los números no deben citarse públicamente** hasta que se resuelvan las caveats documentadas (principalmente los 3 rows faltantes en la condición G).

---

## 10. Cómo correr el proyecto

### Setup inicial

```bash
# Clonar el repo
git clone <repo>
cd TritonGen

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Verificar instalación
python -c "import triton; print(triton.__version__)"
python -c "import xgrammar; print('xgrammar OK')"
```

### Correr los tests

```bash
# Todos los tests
pytest -v

# Solo shared (sin necesitar GPU)
pytest shared/tests/ -v

# Solo gramática
pytest cluster1/tests/test_grammar.py -v

# Solo repair loop
pytest cluster2/tests/test_repair_loop.py -v
```

### Correr Cluster 1 (local, sin GPU — para desarrollo)

```bash
# Condición baseline, kernel elementwise, 1 muestra
python -m cluster1.experiments.run_cluster1 \
    --condition none \
    --kernel-class elementwise \
    --n 1 \
    --output /tmp/test_c1.jsonl
```

### Correr Cluster 1 (Modal, con GPU)

```bash
# Requiere autenticación Modal: `modal token new`
python -m cluster1.experiments.run_cluster1_modal \
    --condition G \
    --n 20
```

### Correr Cluster 2 (Modal)

```bash
python -m cluster2.experiments.run_cluster2_modal \
    --condition C \
    --scale-tier paper
```

### Analizar resultados

```bash
python -m shared.analysis.factorial \
    --input outputs/cluster1/baseline_repaired_l4_n20.jsonl \
    --input outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl \
    --input outputs/cluster2/c_paper_n20_l4.jsonl \
    --input outputs/cluster2/g_plus_c_paper_n20_l4.jsonl \
    --output outputs/analysis/test_analysis.json
```

---

## 11. Tests manuales explicados

Esta sección te guía por experimentos manuales pequeños que revelan cómo funciona cada parte del sistema. El objetivo no es simplemente "que pase el test", sino **entender por qué funciona así**.

---

### Test M-1: Verificar que el schema EvalResult es estable

**Qué aprenderás**: cómo funciona la serialización de datos y por qué los campos desconocidos se rechazan.

```bash
python -c "
from shared.eval.schema import EvalResult
import json

# Crear un EvalResult mínimo
r = EvalResult(
    kernel_id='test_k1',
    kernel_name='elementwise_relu',
    kernel_class='elementwise',
    condition='none',
    sample_index=0,
    model_id='test-model',
    run_id='test-run',
    source='@triton.jit\ndef k(): pass',
    level_reached=0,
    parse_success=False,
    parse_error='SyntaxError',
)

# Serializar
data = r.to_dict()
print('Serializado OK. Campos:', len(data))

# Deserializar
r2 = EvalResult.from_dict(data)
print('Deserializado OK. kernel_id:', r2.kernel_id)

# Intentar con un campo desconocido (debe fallar)
data['campo_inventado'] = 'valor'
try:
    r3 = EvalResult.from_dict(data)
    print('ERROR: debería haber rechazado el campo desconocido')
except Exception as e:
    print('Correcto — campo desconocido rechazado:', type(e).__name__)
"
```

**Por qué se rechazan campos desconocidos**: si un campo nuevo se añade al schema y los artefactos viejos lo tienen como `None`, eso es aceptable. Pero si un artefacto tiene un campo que el schema no conoce, indica que fue generado con una versión diferente del código y puede ser inconsistente.

---

### Test M-2: Explorar la gramática Triton

**Qué aprenderás**: qué acepta y qué rechaza la gramática GBNF, y por qué la gramática es task-agnostic.

```bash
python -c "
from cluster1.grammar.triton_kernel_validator import validate_kernel

# Kernel válido
valid_kernel = '''
import triton
import triton.language as tl

@triton.jit
def add_kernel(x_ptr, y_ptr, output_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)
'''

result = validate_kernel(valid_kernel)
print('Kernel válido acepta:', result.accepted)

# Kernel inválido (usa torch dentro de @triton.jit — no permitido)
invalid_kernel = '''
import triton
import triton.language as tl
import torch

@triton.jit
def bad_kernel(x_ptr, n):
    x = torch.tensor([1, 2, 3])  # torch no se puede usar dentro de @triton.jit
    tl.store(x_ptr, x)
'''

result2 = validate_kernel(invalid_kernel)
print('Kernel inválido acepta:', result2.accepted)
print('Razón de rechazo:', result2.rejection_reason)
"
```

**Por qué importa**: la gramática define exactamente qué patrones de código Triton son sintácticamente posibles. Durante la generación, xgrammar usa esto para enmascarar tokens que llevarían a código fuera del lenguaje — antes de que el LLM los genere.

---

### Test M-3: Simular el repair loop sin GPU

**Qué aprenderás**: la lógica del repair loop independientemente de la generación LLM.

```bash
python -c "
from cluster2.feedback.repair_loop import RepairLoop, RepairGenerationInput

# Simular un loop con un generador mock
class MockGenerator:
    def __init__(self, fail_first_n=2):
        self.call_count = 0
        self.fail_first_n = fail_first_n
    
    def generate(self, prompt, attempt_index):
        self.call_count += 1
        if self.call_count <= self.fail_first_n:
            # Simular fallo: código que no compila
            return '@triton.jit\ndef k(x): SYNTAX ERROR HERE'
        else:
            # Simular éxito
            return '@triton.jit\ndef k(x_ptr, n, BLOCK: tl.constexpr): pass'

mock_gen = MockGenerator(fail_first_n=2)
loop = RepairLoop(budget=5, generator=mock_gen)

# Correr el loop
result = loop.run(kernel_spec='elementwise_relu', prompt='...')
print('Converged:', result.converged)
print('Intentos necesarios:', result.attempts_used)
print('Traces:', len(result.traces))
for i, trace in enumerate(result.traces):
    print(f'  attempt {i}: level_reached={trace.level_reached}')
"
```

**Por qué el budget es 5**: el análisis previo mostró que la tasa marginal de éxito cae significativamente después del 3er intento. Budget=5 es conservador — da margen para casos difíciles sin un costo prohibitivo de inferencia.

---

### Test M-4: Verificar la taxonomía de fallos

**Qué aprenderás**: cómo se clasifican los errores y por qué los códigos normalizados son mejores que strings libres.

```bash
python -c "
from shared.eval.failure_taxonomy import classify_failure, FailureCode

# Test con diferentes tipos de error
test_cases = [
    ('SyntaxError: invalid syntax', None, 'parse'),
    (None, 'triton.compiler.errors.CompilationError: ...\nexpected int, got float', 'compile'),
    (None, None, 'pass'),  # sin error
]

for parse_err, compile_err, expected in test_cases:
    code = classify_failure(
        parse_error=parse_err,
        compile_error=compile_err,
    )
    print(f'[{expected}] -> código: {code}')

# Verificar que todos los códigos conocidos existen
print()
print('Todos los códigos de fallo:')
for code in FailureCode:
    print(f'  {code.value}')
"
```

---

### Test M-5: Leer y analizar un artefacto JSONL real

**Qué aprenderás**: la estructura de los datos de resultados y cómo interpretar las métricas.

```bash
python -c "
import json
from pathlib import Path

# Leer el artefacto de Cluster 1, condición none
path = Path('outputs/cluster1/baseline_repaired_l4_n20.jsonl')
if not path.exists():
    print('Artefacto no encontrado. Usando datos simulados.')
    exit()

rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

print(f'Total de rows: {len(rows)}')
print()

# Distribución por kernel
from collections import Counter
by_kernel = Counter(r['kernel_name'] for r in rows)
print('Rows por kernel:', dict(by_kernel))
print()

# Tasa de compilación por kernel
for kernel_name in ['elementwise_relu', 'reduction_softmax', 'matmul_tiled_gemm']:
    kernel_rows = [r for r in rows if r['kernel_name'] == kernel_name]
    compile_ok = sum(1 for r in kernel_rows if r.get('compile_success', False))
    print(f'{kernel_name}: compile@1 = {compile_ok}/{len(kernel_rows)} = {compile_ok/len(kernel_rows):.2%}')

print()

# Distribución de failure codes
failure_codes = Counter(r.get('failure_code') for r in rows)
print('Distribución de fallos:')
for code, count in failure_codes.most_common():
    print(f'  {code}: {count} ({count/len(rows):.1%})')
"
```

---

### Test M-6: Entender qué hace xgrammar durante la decodificación

**Qué aprenderás**: cómo la gramática enmascara tokens en tiempo real durante la generación.

```bash
python -c "
# Este test requiere que xgrammar esté instalado
try:
    import xgrammar
except ImportError:
    print('xgrammar no está instalado — instalar con: pip install xgrammar>=0.1.33')
    exit()

from cluster1.grammar.grammar_loader import load_grammar
from cluster1.generation.constrained_decoding import TritonGrammarLogitsProcessor

# Cargar gramática
grammar = load_grammar(variant='task_agnostic')
print('Gramática cargada. Tamaño:', len(str(grammar)))

# Simular un tokenizer básico para ver la máscara
import torch

# Si tienes un tokenizer disponible:
try:
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained('codellama/CodeLlama-7b-hf')
    processor = TritonGrammarLogitsProcessor(grammar, tokenizer)
    
    # Crear logits dummy
    fake_logits = torch.zeros(1, tokenizer.vocab_size)
    
    # Aplicar máscara — muchos tokens deberían quedar en -inf
    masked = processor(None, fake_logits)
    n_valid = (masked[0] > -1e9).sum().item()
    n_total = tokenizer.vocab_size
    print(f'Al inicio del kernel: {n_valid}/{n_total} tokens válidos ({n_valid/n_total:.1%})')
    print('La gramática restringe al', f'{(1 - n_valid/n_total):.1%}', 'del vocabulario')
except Exception as e:
    print('Tokenizer no disponible localmente:', e)
    print('Para ejecutar esto completo, necesitas el modelo descargado.')
"
```

**Por qué esto importa**: la tasa de tokens enmascarados es un proxy de cuánta "ayuda" está dando la gramática. Si al principio del kernel solo el 5% del vocabulario es válido, la gramática está haciendo mucho trabajo. Si es el 80%, está dejando casi total libertad al modelo.

---

### Test M-7: Verificar que el análisis factorial es correcto

**Qué aprenderás**: cómo se computan los efectos estadísticos y qué significan los números.

```bash
python -c "
from shared.analysis.factorial import FactorialAnalyzer
import json

# Datos sintéticos de 4 celdas (none, G, C, G+C)
# Cada celda tiene 60 filas (20 samples × 3 kernels)
import random
random.seed(42)

def make_cell(condition, pass_rate, n=60):
    return [
        {'condition': condition, 'functional_success': random.random() < pass_rate}
        for _ in range(n)
    ]

data = (
    make_cell('none', 0.20) +  # 20% pass rate sin nada
    make_cell('G', 0.35) +     # gramática ayuda +15pp
    make_cell('C', 0.40) +     # correctness ayuda +20pp
    make_cell('G+C', 0.65)     # G+C: ¿hay sinergia?
)

analyzer = FactorialAnalyzer(data)
result = analyzer.run()

print('Resultados del análisis factorial (datos sintéticos):')
print()
for cell in result['cells']:
    print(f\"Condición {cell['condition']:6s}: pass@1 = {cell['pass_at_1']:.2%} (CI: [{cell['ci_low']:.2%}, {cell['ci_high']:.2%}])\")

print()
print('Efectos principales:')
print(f\"  Efecto de G:   OR = {result['effects']['G']['odds_ratio']:.2f}\")
print(f\"  Efecto de C:   OR = {result['effects']['C']['odds_ratio']:.2f}\")
print(f\"  Interacción:   OR = {result['effects']['GxC']['odds_ratio']:.2f}\")
print()
print('Si interacción OR > 1: G y C se potencian mutuamente.')
print('Si interacción OR ≈ 1: efectos son aditivos independientes.')
"
```

---

### Test M-8: Verificar integridad de artefactos

**Qué aprenderás**: cómo el sistema verifica que los artefactos no han sido modificados.

```bash
python -c "
import hashlib, json
from pathlib import Path

def hash_jsonl(path):
    content = Path(path).read_bytes()
    return hashlib.sha256(content).hexdigest()

artifacts = [
    'outputs/cluster1/baseline_repaired_l4_n20.jsonl',
    'outputs/cluster1/task_agnostic_g_aligned_pipeline_n20_l4.jsonl',
    'outputs/cluster2/c_paper_n20_l4.jsonl',
    'outputs/cluster2/g_plus_c_paper_n20_l4.jsonl',
]

print('Hashes de artefactos actuales:')
for path in artifacts:
    p = Path(path)
    if p.exists():
        h = hash_jsonl(path)
        rows = len(p.read_text().strip().splitlines())
        print(f'  {p.name}: sha256={h[:16]}... ({rows} rows)')
    else:
        print(f'  {p.name}: NO ENCONTRADO')

print()
print('Estos hashes deben coincidir con los registrados en docs/05_artifacts_and_results_registry.md')
print('Si no coinciden, el artefacto fue modificado o regenerado.')
"
```

---

### Test M-9: End-to-end local mínimo (sin GPU)

**Qué aprenderás**: el flujo completo de generación → evaluación → JSONL usando un kernel dummy.

```bash
python -c "
from shared.eval.schema import EvalResult
from shared.eval.pipeline import EvalPipeline
from shared.eval.failure_taxonomy import FailureCode
import json, time

# Kernel Triton válido pero trivialmente incorrecto numéricamente
# (multiplicar por 2 cuando debería ser identity)
dummy_source = '''
import triton
import triton.language as tl

@triton.jit
def buggy_relu(x_ptr, output_ptr, n, BLOCK: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK + tl.arange(0, BLOCK)
    mask = offsets < n
    x = tl.load(x_ptr + offsets, mask=mask)
    # Bug: debería ser max(x, 0) pero multiplica por 2
    out = x * 2.0
    tl.store(output_ptr + offsets, out, mask=mask)
'''

# Simular el pipeline hasta L0 (sin GPU)
pipeline = EvalPipeline(skip_levels=['compile', 'correctness', 'sanitizer', 'performance'])

result = pipeline.run(
    source=dummy_source,
    kernel_id='test_local_dummy',
    kernel_name='elementwise_relu',
    kernel_class='elementwise',
    condition='none',
    sample_index=0,
    model_id='test',
    run_id='local_test_' + str(int(time.time())),
)

print('EvalResult generado:')
print(f'  level_reached: {result.level_reached}')
print(f'  parse_success: {result.parse_success}')
print(f'  has_triton_decorator: {result.has_triton_decorator}')
print(f'  failure_code: {result.failure_code}')
print()

# Serializar a JSONL
row = json.dumps(result.to_dict())
print('Fila JSONL (primeros 200 chars):')
print(row[:200] + '...')
"
```

---

## 12. Preguntas frecuentes / trampas comunes

### ¿Por qué hay 177 rows en la condición G en vez de 180?

Los 3 rows faltantes son: `matmul_tiled_gemm` con `dtype=fp32` seed 5, y `dtype=bf16` seeds 0 y 18. Hay un issue de reproducibilidad documentado en los audits — la gramática en esas combinaciones específicas causó timeout durante la generación. Los análisis actuales marcan esto como caveat y usan `metadata.reportable=false`.

### ¿Por qué `metadata.reportable = false` en el análisis?

Significa que los números son computacionalmente correctos pero **no deben citarse en un paper** todavía. El criterio para `reportable=true` es: 180/180 rows en todas las celdas, sin caveats abiertos en los audits. Ver `docs/05_artifacts_and_results_registry.md`.

### ¿Puedo correr esto sin Modal?

Sí, parcialmente. El pipeline de evaluación L0 (parse) corre localmente. L1 (compile) requiere GPU (Triton no compila en CPU con las mismas garantías). L2 (correctness) también requiere GPU. Para desarrollo local, usa los tests que mockean las capas remotas.

### ¿Qué es `modal_image_sha` y por qué aparece en cada row?

Es el hash SHA256 de la imagen Docker que construyó Modal para ese run. Garantiza que todos los rows de un run usaron exactamente el mismo entorno (misma versión de Triton, misma versión de xgrammar, etc.). Si dos rows tienen distinto `modal_image_sha`, fueron generados en entornos diferentes y no son directamente comparables.

### ¿Por qué xgrammar y no constraintdecoder / otros?

xgrammar compila el GBNF a un autómata determinista finito que evalúa aceptación de tokens en O(1) por token. Alternativas como Guidance usan regex y son más lentas para gramáticas complejas. La velocidad importa porque la decodificación es el cuello de botella.

### ¿Cómo sé qué versión del modelo se usó?

Cada `EvalResult` tiene `model_id`, `model_revision` (commit hash de HuggingFace), y `tokenizer_revision`. Esto permite reproducir exactamente la misma generación incluso si el modelo tiene versiones nuevas en HuggingFace.

### El repair loop dice `repair_converged=False` — ¿es un fallo del sistema?

No. Significa que el LLM no logró producir un kernel correcto dentro del budget de 5 intentos. Es un resultado experimental válido. El análisis computa `convergence_rate = rows donde repair_converged=True / total rows C o G+C`.

---

## 13. Glosario

| Término | Definición |
|---------|-----------|
| **Triton** | Lenguaje de programación para GPU kernels (de OpenAI). Similar a CUDA pero con abstracción de tiles. |
| **Kernel** | Función que corre en GPU de forma masivamente paralela. |
| **GBNF** | Grammar Backus-Naur Form — variante de BNF usada por xgrammar y llama.cpp para constrained decoding. |
| **xgrammar** | Librería de constrained decoding que compila gramáticas GBNF a autómatas. |
| **Modal** | Plataforma de cloud computing especializada en ML workloads. |
| **Constrained decoding** | Técnica de generación LLM donde se enmascaran tokens inválidos según una gramática antes de cada paso de sampling. |
| **EvalResult** | Dataclass Python que representa un resultado de evaluación. La unidad atómica de datos del sistema. |
| **JSONL** | JSON Lines — formato donde cada línea es un JSON independiente. Eficiente para streaming y append. |
| **pass@k** | Probabilidad de que al menos 1 de k muestras independientes pase la evaluación. |
| **Repair loop** | Bucle iterativo donde el LLM recibe feedback de su error anterior y genera una versión corregida. |
| **Factor** | En el diseño factorial: variable binaria (ON/OFF). G, C, P son los tres factores. |
| **Celda** | Combinación específica de factores: none=(G=0,C=0), G=(G=1,C=0), C=(G=0,C=1), G+C=(G=1,C=1). |
| **Bootstrap CI** | Intervalo de confianza computado por remuestreo repetido, sin asumir distribución normal. |
| **Level reached** | Nivel máximo de evaluación que superó un kernel (0=parse, 1=compile, 2=correctness, 3=safe, 4=perf). |
| **Provenance** | Metadatos que permiten trazar el origen exacto de un artefacto (versiones, hashes, timestamps). |
| **Reportable** | Flag que indica si los resultados cumplen todos los criterios para ser citados en un paper. |

---

## 14. Mapa de docs existentes

Los docs en `docs/` son citation-grade — revisados y verificados. Esta es su función:

| Archivo | Cuándo leerlo |
|---------|--------------|
| `00_project_map.md` | Orientación inicial — scope actual, qué está listo |
| `02_methodology_cluster1.md` | Detalles de la generación con gramática (G factor) |
| `03_methodology_cluster2.md` | Detalles del repair loop (C factor) |
| `04_modal_infrastructure.md` | Setup de Modal, builds de imagen, secrets |
| `05_artifacts_and_results_registry.md` | Qué artefactos existen, su estado, caveats |
| `06_failure_taxonomy_and_eval_ladder.md` | Códigos de fallo detallados, thresholds de evaluación |
| `07_analysis_and_statistics.md` | Metodología estadística, cómo interpretar los números |
| `08_decision_log.md` | Historia de decisiones de diseño (muy útil para entender el "por qué") |
| `09_preliminary_report_outline.md` | Estructura del paper final |
| `10_cluster3_drift_prevention_plan.md` | Plan para el factor P (performance) |
| **`ONBOARDING.md`** | ← **Este documento** |

Los audits en `audits/` son registros históricos de verificación. Son útiles para entender qué salió mal en cada fase, pero **no son fuente de verdad** — la fuente de verdad son los docs y los artefactos JSONL.

---

*Última actualización: 2026-05-21*
*Basado en el estado del repo en commit `96efd96` (Docs Update)*
