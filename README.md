[![PyPI](https://img.shields.io/pypi/v/ctxure.svg)](https://pypi.org/project/ctxure/)
[![Python versions](https://img.shields.io/pypi/pyversions/ctxure.svg)](https://pypi.org/project/ctxure/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![codecov](https://codecov.io/gh/cpcprmrm/ctxure/branch/main/graph/badge.svg)](https://codecov.io/gh/cpcprmrm/ctxure)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)


# Ctxure

Ctxure is a type-driven, context-aware data conversion framework. Conversion rules depend not just on a value's type but also on where it sits in the object graph, expressed declaratively. It ships with default behavior for converting unstructured data (e.g., a JSON dict) to structured data (e.g., a dataclass or `TypedDict`), and back.


## Installation

```bash
pip install ctxure
```

```python
import ctxure
```

## Rationale

### Why Ctxure?

The primary focus is the context-aware hook system: target type, root type (the conversion entry), owner type, and location in the object graph are all available as axes for registering hooks declaratively.
A second characteristic is clean, non-intrusive separation of conversion logic from the domain model. Ctxure does not require you to extend a library-specific base class or embed validation and transformation logic in the domain model.
In this way, Ctxure serves as a bridge between data models of different layers.

This is especially useful when you need type-driven data mapping across heterogeneous or evolving sources. Domain models are usually stable, and sometimes you have no control over them at all (e.g., when they are owned or provided by a third party). Yet you may still need to transform heterogeneous or evolving external data into those models. Ctxure keeps that friction low.

```python
# The problem: Same type, different conversion depending on the context.

# By root type, expand department codes when exporting
@register
def structure_hook(ctx: Ctx[Employee, Under[ExportHRReport]], data: str) -> Employee:
    ...

# By owner type, only name is erased; Ctxure handles the rest
@register
def structure_hook(ctx: Ctx[Employee, Of[Anonymized]], data: str) -> Employee:
    ...

# By location, legacy format in a specific field
@register
def structure_hook(ctx: Ctx[Employee, "$.managed_in_old_db[?]"], data: str) -> Employee:
    ...
```

See [Examples](#examples) for the full development of this example.

### Why not Ctxure?

Ctxure is not the fastest option. For most IO-bound applications the overhead is negligible, but if maximum throughput is a hard requirement, Ctxure may not be the right choice. Ctxure also focuses narrowly on data conversion and does not provide features like JSON schema generation or standalone runtime validation outside the conversion process.

## Examples

The examples build up progressively. If you want something interesting first, start from the [Root type](#root-type) example instead of the [Basic usage](#basic-usage) below.

### Basic usage

Let's start with a basic example. Ctxure provides `structure` and `unstructure` functions, following the conventions of [cattrs](https://github.com/python-attrs/cattrs).

```python
from ctxure import structure, unstructure
from dataclasses import dataclass

@dataclass
class Employee:
    name: str
    department: str

records = [
    {"name": "jack", "department": "data"},
    {"name": "jane", "department": "sales"}
]

structured = structure(list[Employee], records)
# [Employee('jack', 'data'), Employee('jane', 'sales')]

unstructure(list[Employee], structured)
# == records

structure(Employee, {"name": "jade"})
# MissingFields exception raised.
```

This demonstrates Ctxure's default behavior of structuring a `dict` into a dataclass. Ctxure supports `TypedDict`, `Literal`, `NewType`, union, etc. See [Default behavior](#default-behavior) for the supported types out of the box.

### User-defined hooks

Suppose that the preferred representation of an employee in unstructured data is a string "name@department" instead of a `dict`. We can write a hook to support the representation.

```python
from ctxure import register, Ctx, ValidationError

# A helper to parse the string representation
def parse_employee(data: str) -> tuple[str, str]:
    splits = data.split("@")
    if len(splits) != 2 or not all(splits):
        raise ValueError("Invalid employee format")
    return splits[0], splits[1]

# A hook to structure the string representation
@register
def structure_hook(ctx: Ctx[Employee], data: str) -> Employee:
    try:
        name, department = parse_employee(data)
        return Employee(name, department)
    except ValueError as e:
        raise ValidationError(ctx, data, str(e)) from e

# A hook to unstructure as the string representation
@register
def unstructure_hook(ctx: Ctx[Employee], data: Employee) -> str:
    return f"{data.name}@{data.department}"

records = ["jack@data", "jane@sales"]

structured = structure(list[Employee], records)
# [Employee('jack', 'data'), Employee('jane', 'sales')]

unstructure(list[Employee], structured)
# ['jack@data', 'jane@sales']

structure(list[Employee], ["john:infra"])
# ValidationError: Invalid employee format (at $[0])

# Dict representation still works
records = [
    {"name": "jack", "department": "data"},
    {"name": "jane", "department": "sales"}
]

structure(list[Employee], records)
# [Employee('jack', 'data'), Employee('jane', 'sales')]
```

Note that the `dict` representation still works. If we want to forbid it, we can register a hook with `data: dict` and raise an exception. Hooks take priority over default handlers.

The `ctxure.register` decorator registers hooks. Hook names are fixed as `structure_hook` and `unstructure_hook`. Any number of hooks can be registered under these two fixed names.
Ctxure's hook system is built on top of its own internal [multiple dispatch](https://en.wikipedia.org/wiki/Multiple_dispatch) ("overloading" dispatched by runtime type) system. This is like registering multiple versions of `structure_hook` or `unstructure_hook` with different argument signatures.

At runtime, `ctx` represents the current context. The hook body can use properties of `ctx` and utility functions working with `ctx` to inspect the current context. They are also useful for debugging. See [Ctx](#ctx) for details.

### Root type

Sometimes the same domain type needs different conversion depending on *what's being converted overall*. Suppose the HR system stores departments as short codes internally but expands them to full names when exporting employee records to external consumers.

`Under[Root]` selects by the root of the conversion entry — the type passed to `structure` or `unstructure`.

```python
from ctxure import Under, structure_by_type
from dataclasses import replace

@dataclass
class HRReport:
    employees: list[Employee]

@dataclass
class ExportHRReport:
    employees: list[Employee]

DEPT_NAMES = {"ENG": "Engineering", "SAL": "Sales", "DAT": "Data Science"}

# Fires only when the conversion was entered at ExportHRReport.
# Inside an HRReport, the previously-registered Ctx[Employee] hook runs unchanged.
@register
def structure_hook(ctx: Ctx[Employee, Under[ExportHRReport]], data: str) -> Employee:
    # Structure with only target type, stripping owner type, root type, and path.
    # The hook defined in the previous example is called.
    employee = structure_by_type(ctx, data)
    return replace(
        employee,
        department=DEPT_NAMES.get(employee.department, employee.department)
    )

records = ["jack@ENG", "jane@SAL"]

structure(HRReport, {"employees": records})
# HRReport(employees=[Employee("jack", "ENG"), Employee("jane", "SAL")])

structure(ExportHRReport, {"employees": records})
# ExportHRReport(employees=[Employee("jack", "Engineering"), Employee("jane", "Sales")])
```

`structure_by_type(ctx, data)` strips all contextual information except the structured type and runs a hook registered with only the target type, or the default handler if no such hook exists. Here it falls through to the `Ctx[Employee]` hook from the previous section, after which we apply the expansion. `unstructure_by_type` is also available. Note that child contexts (for fields or elements) carry owner type information, while root type and path remain suppressed.

`Under` composes with the other axes; you can combine it freely with target type, owner, and path — e.g., `Ctx[Employee, Of[Department], Under[ExportHRReport]]` to scope further.

Note that if there are multiple hooks matching the context, a hook registered with the most specific context wins over less specific ones. The hook defined in this example (with `Ctx[Employee, Under[ExportHRReport]]`) is more specific than the previous one (with `Ctx[Employee]`). So if the root is `ExportHRReport`, the hook in this example is fired. See [Hook resolution](#hook-resolution) and [Conflict resolution](#conflict-resolution) for details of the hook dispatch.

### Owner type

Now assume that some downstream tasks want anonymized data to protect private information.
The downstream task API has wrapper types `Anonymized[T]` and `Transparent[T]` to mark whether the contents should be anonymized.

In this example, we use the `Of` parameter to express the owner type.

```python
from ctxure import Of, structure_by_type
from dataclasses import replace

@dataclass
class Anonymized[T]:
    person: T

@dataclass
class Transparent[T]:
    person: T

# This hook works on both string and dict representations.
@register
def structure_hook(ctx: Ctx[Employee, Of[Anonymized[Employee]]], data: str | dict) -> Employee:
    employee = structure_by_type(ctx, data)
    return replace(employee, name="")

record = {"person": "jack@frontend"}

structure(Anonymized[Employee], record)
# Anonymized(Employee('', 'frontend'))

structure(Transparent[Employee], record)
# Transparent(Employee('jack', 'frontend'))

record_in_dict = {"person": {"name": "jack", "department": "frontend"}}

structure(Anonymized[Employee], record_in_dict)
# Anonymized(Employee('', 'frontend'))

structure(Transparent[Employee], record_in_dict)
# Transparent(Employee('jack', 'frontend'))
```

Note that we could instead write `Ctx[Anonymized[Employee]]` to fire on the wrapper itself. Both forms are valid; the choice depends on what we want to control.
A `Ctx[Anonymized[Employee]]` hook takes ownership of the whole wrapper construction (extracting `person`, building the `Anonymized` instance, and so on). This is useful when we want the hook to reshape the wrapper itself, e.g., change its field layout or emit a different result type.
The `Of` form above instead lets Ctxure's default wrapper handling stand and overrides only the inner `Employee` transformation, keeping the hook focused on the anonymization logic and unaffected by (future) changes in `Anonymized`'s field set.

Compared to the [Root type](#root-type) example above, `Of` selects by the *directly* surrounding container at this position, while `Under` selects by the type at the top of the conversion. Use `Of` when a wrapper type around the value tells you what to do; use `Under` when the mode is decided once at the entry point and applies everywhere underneath.

### Scoped hooks

What if some downstream tasks need fake unique names instead of erased names? We can use scoped hooks.

```python
import uuid
from ctxure import ctxure_config

# This copy is independent of the original `register` but has already registered hooks.
register_with_random_uuid_name = register.copy()

# Now this overrides the Of-anonymization hook from the Owner type example, but only in the scope of `register_with_random_uuid_name`.
@register_with_random_uuid_name
def structure_hook(ctx: Ctx[Employee, Of[Anonymized[Employee]]], data: str | dict) -> Employee:
    employee = structure_by_type(ctx, data)
    return replace(employee, name=str(uuid.uuid4()))

# Apply the scope
with ctxure_config(dispatcher=register_with_random_uuid_name):
    structure(Anonymized[Employee], record)
    # Anonymized(Employee('3dc46dd4-22f2-...', 'frontend'))

# The global scope
structure(Anonymized[Employee], record)
# Anonymized(Employee('', 'frontend'))
```

### Path-aware hooks

Suppose that employee information in a specific path has a different format "name:department". We can register hooks with [JSONPath](https://en.wikipedia.org/wiki/JSONPath)-like path expressions.

This example demonstrates a targeted fix for a messy real-world situation. Such fixes are usually ad hoc. However, Ctxure keeps it declarative and scoped — the model stays clean, and the format quirk doesn't leak beyond its hook.

```python
@dataclass
class EmployeeRegistry:
    managed_in_new_db: list[Employee]
    managed_in_old_db: list[Employee]

@register
def structure_hook(ctx: Ctx[Employee, "$.managed_in_old_db[?]"], data: str) -> Employee:
    parsed = data.split(":")
    if len(parsed) != 2 or not all(parsed):
        raise ValidationError(ctx, data, "Invalid legacy employee format")
    return Employee(*parsed)

records = {
    "managed_in_new_db": ["jack@data", "jane@sales"],
    "managed_in_old_db": ["john:infra", "joel:infra"]
}
structure(EmployeeRegistry, records)
# EmployeeRegistry(
#     [Employee("jack", "data"), Employee("jane", "sales")]
#     [Employee("john", "infra"), Employee("joel", "infra")]
# )
```

The path expression also supports rootless location. For example, `Ctx[".foo"]` means a field `foo` of whatever dataclass or TypedDict in any location. See also [Hooks for a single field or item](#hooks-for-a-single-field-or-item) and [Path expression](#path-expression).

### Pre- and post-validation

Suppose that we need to reject list processing if the list is too long.

```python
from ctxure import structure_default

@register
def structure_hook(ctx: Ctx[list[Employee]], data: list[Any]) -> list[Employee]:
    if len(data) > 100:
        raise ValidationError(ctx, data, "Too large data")
    return structure_default(ctx, data)

structure(list[Employee], records * 100)
# ValidationError: Too large data (at $)
```

Forwarding to `structure_default` runs the default handler. You can use it for pre- and post-validation: validate the data, call `structure_default`, then validate the result — or modify and return it. It bypasses any hooks for the current context; hooks for children (fields or elements) still fire.

You may be tempted to write `data: list[str]` instead of `data: list[Any]`. However, this raises an error at registration time due to Python's limited runtime generic type information. You can use `list[str]` as a parameter of `Ctx`, but not as a top-level hint on the `data` side. See [Restrictions on `data` type](#restrictions-on-data-type) for details.


### Renamed fields

Sometimes the fields of a target dataclass (or `TypedDict`) and the keys of the input data do not match. One option is to call `structure_default` with a modified copy of `data` inside a hook, but that can be inefficient.
`structure_default` and `unstructure_default` accept an optional `keymap: dict[str, str | KeyPath]` argument (any `Mapping` works). `keymap` maps structured keys (field names) to unstructured keys (`dict` keys). For any field not in `keymap`, the input `data` must use the field name as its key. A `KeyPath` value reads from a nested location instead; see [Nested keys](#nested-keys).

It is strongly recommended to define `keymap` as a module-level constant. Defining it as a local variable creates a new `dict` on every call — wasteful on its own, and it also defeats Ctxure's internal cache.

In this example, we use `keymap` to process legacy database entries having "division" instead of "department".

```python
from ctxure import structure_default, unstructure_default

keymap = {"department": "division"}

@register
def structure_hook(ctx: Ctx[Employee, "$.managed_in_old_db[?]"], data: dict) -> Employee:
    return structure_default(ctx, data, keymap=keymap)

@register
def unstructure_hook(ctx: Ctx[Employee, "$.managed_in_old_db[?]"], data: Employee) -> dict:
    return unstructure_default(ctx, data, keymap=keymap)

records = {
    "managed_in_new_db": [
        {"name": "jane", "department": "sales"},
    ],
    "managed_in_old_db": [
        {"name": "john", "division": "infra"},
        {"name": "joel", "division": "infra"}
    ]
}
structured = structure(EmployeeRegistry, records)
# EmployeeRegistry(
#     [Employee('jane', 'sales')],
#     [Employee("john", "infra"), Employee("joel", "infra")]
# )
unstructure(EmployeeRegistry, structured)
# == records
```

### Nested keys

Input data often wraps the values a model needs in nested objects. A `KeyPath` value in `keymap` reads a field from a nested location relative to the current `data`, without copying or reshaping the input.

```python
# This example is independent of the previous ones. So we import all necessary names here.
from ctxure import Ctx, KeyPath, register, structure, structure_default
from dataclasses import dataclass

@dataclass
class Order:
    order_id: str
    customer: str
    total: float

keymap = {"customer": KeyPath("buyer", "email"), "total": KeyPath("payment", "amount")}

@register
def structure_hook(ctx: Ctx[Order], data: dict) -> Order:
    return structure_default(ctx, data, keymap=keymap)

structure(Order, {
    "order_id": "A-1001",
    "buyer": {"email": "kim@example.com", "tier": "gold"},
    "payment": {"amount": 42.5, "currency": "EUR"},
})
# Order(order_id='A-1001', customer='kim@example.com', total=42.5)
```

Each argument of `KeyPath` is one literal `dict` key, so no escaping is needed: `KeyPath("user.name")` is the single key `"user.name"`. A missing key at any depth is treated like a missing field, and a value on the way that is not a `dict` (including `None`) raises `ValidationError`. Several fields may read overlapping locations.

Extra keys are checked only at the current level. Here `"buyer"` and `"payment"` count as used, and the keys inside them that no field reads, such as `"tier"` and `"currency"`, are ignored. Note that `KeyPath` refers to the unstructured data, while [path expressions](#path-expression) in `Ctx` refer to the structured data. So hooks registered for a field's path, such as `"$.customer"`, still fire.

`unstructure_default` does not support multi-key `KeyPath`s yet and raises `ValidationError` for them.

### Injecting extra data

You may want to thread extra data through the transformation process and use it in hooks — for example, to inject dependencies or control hook behavior. Call `structure` or `unstructure` with the optional `extra=your_extra_data` argument and read it via `get_extra(ctx)` inside hooks. `get_extra` returns the same object you passed; mutate it directly to share state across hooks (e.g., pass `extra={}` and mutate the dict).

```python
from typing import Any
from ctxure import get_extra

@register
def structure_hook(ctx: Ctx[Employee], data: str) -> Employee:
    try:
        name, department = parse_employee(data)
        if get_extra(ctx)["mask-name"]:
            name = "*"
        return Employee(name, department)
    except ValueError as e:
        raise ValidationError(ctx, data, str(e)) from e

records = [
    ["jack@data", "jane@sales"],
    ["john@infra"]
]

structure(list[list[Employee]], records, extra={"mask-name": False})
# [
#     [Employee('jack', 'data'), Employee('jane', 'sales')],
#     [Employee('john', 'infra')]
# ]

structure(list[list[Employee]], records, extra={"mask-name": True})
# [
#     [Employee('*', 'data'), Employee('*', 'sales')],
#     [Employee('*', 'infra')]
# ]
```


### Hooks for a single field or item

`Ctx[".foo"]` means a field `foo`. Such a hook fires for any field named `foo` of a dataclass or a `TypedDict`. We can also specify the owner type, like `Ctx[".foo", Of[Foo]]` where `Foo` is a dataclass or a `TypedDict`. Such a hook fires only for `Foo.foo`. The field type can also be constrained, like `Ctx[".foo", int]`. Such a hook fires if the field is `foo` and its type is `int`. We can use `Ctx[".?", Of[Foo]]` to denote any field of `Foo`.

You can also use `Ctx["[0]"]` to denote the first element of any `Sequence`, or a dict value at integer key `0`. The type and owner type can be constrained here as well.

In this example, we use `Ctx[".?", Of[Foo]]` to validate each field of `Foo` in a uniform way. Suppose that validation logic is given as field metadata (say, by a third party) and we must use it. Note, however, that Ctxure does not require field metadata in any way.

```python
# This example is independent of the previous ones. So we import all necessary names here.
from ctxure import register, structure, structure_default, Ctx, Of, ValidationError
from dataclasses import dataclass, field
from typing import Any

@dataclass
class User:
    name: str = field(metadata={
        "validator": lambda x: None if len(x) > 3 else "Too short name"
    })
    age: int = field(metadata={
        "validator": lambda x: None if x >= 0 else "Negative age"
    })

# Here the rootless path expression ".?" means any field.
@register
def structure_hook(ctx: Ctx[".?", Of[User]], data: Any) -> Any:
    if validator := ctx.field.metadata.get("validator"):
        error = validator(data)
        if error:
            raise ValidationError(ctx, data, error)
    return structure_default(ctx, data)

structure(User, {"name": "jack", "age": 20})
# User('jack', 20)

structure(User, {"name": "ja", "age": 20})
# ValidationError: Too short name (at $.name)

structure(User, {"name": "jack", "age": -1})
# ValidationError: Negative age (at $.age)
```
Note also that `__post_init__`, which may have post-validation logic, works as expected transparently.

If we register an additional hook with more specific context, it has higher priority than the one in the example. For example, if a new hook with `Ctx[".name", Of[User]]` is registered, it is fired instead of the one in the example. So, the new one should implement its own validation.

### Reading root and sibling data

A hook sometimes needs context from outside its current position — typically, root-level data that drives behavior deep in the tree.

```python
# This example is independent of the previous ones. So we import all necessary names here.
from ctxure import Ctx, Of, get_data, get_root, register, structure
from dataclasses import dataclass
from typing import Literal

@dataclass
class Section:
    title: str
    body: str

@dataclass
class Report:
    mode: Literal["summary", "full"]
    sections: list[Section]

# Body content is truncated when the whole report is in summary mode.
@register
def structure_hook(ctx: Ctx[".body", Of[Section]], data: str) -> str:
    root_data = get_data(get_root(ctx))
    if root_data["mode"] == "summary":
        return data[:80] + "…"
    else:
        return data

body = "We had a strong quarter across all regions. Revenue grew 12% year over year, driven by enterprise renewals and faster onboarding."
structure(Report, {"mode": "summary", "sections": [{"title": "Q1", "body": body}]})
# Report(mode="summary", sections=[Section(title="Q1", body="We had a strong quarter across all regions. Revenue grew 12% year over year, dri…")])

structure(Report, {"mode": "full", "sections": [{"title": "Q1", "body": body}]})
# Report(mode="full", sections=[Section(title="Q1", body="We had a strong quarter across all regions. Revenue grew 12% year over year, driven by enterprise renewals and faster onboarding.")])
```

`get_data(ctx.parent)` is also available for sibling access under the same parent. See [Context](#context) for available information via `ctx`.

If `mode` were instead a type-level distinction (e.g., a `SummaryReport` vs `FullReport` wrapper type), [Root type](#root-type) would be the right tool — `Under[SummaryReport]` selects by the entry type, not by a runtime field value. Use `get_data(get_root(ctx))` when the discriminating value is part of the data itself.

### Union discrimination

When a union member is a dataclass or `TypedDict`, Ctxure discriminates members automatically. Two mechanisms apply, and they compose:

- **Tag-based**: a field declared as `Literal[<single_value>]` acts as a discriminator tag when each member declares a different literal value for it.
- **Field-based**: which required fields are present (and which fields declared by *other* members are absent) selects the matching member.

After discrimination, Ctxure checks for a hook matching the current context with the union type replaced by the chosen member type; if one exists, it fires.

See [structure](#structure) and [unstructure](#unstructure) for more details on union discrimination.

```python
# This example is independent of the previous ones. So we import all necessary names here.
from ctxure import structure
from dataclasses import dataclass
from typing import Literal

@dataclass
class TextMessage:
    type: Literal["text"]
    content: str

@dataclass
class ImageMessage:
    type: Literal["image"]
    url: str

@dataclass
class Error:
    code: int
    message: str

Event = TextMessage | ImageMessage | Error

# Tag-based: picked by the `type` field value.
structure(Event, {"type": "text", "content": "hi"})
# TextMessage(type='text', content='hi')

structure(Event, {"type": "image", "url": "http://x"})
# ImageMessage(type='image', url='http://x')

# Field-based: Error has no `type` field, so it's picked by the presence of its own required fields (`code`, `message`).
structure(Event, {"code": 500, "message": "boom"})
# Error(code=500, message='boom')

# Unknown tag value matches no member.
structure(Event, {"type": "video", "content": "x"})
# NoStructureHook: The data is not compatible with any member of the union (at $)

# Carrying fields exclusive to another member is rejected.
structure(Event, {"type": "text", "content": "hi", "code": 1})
# NoStructureHook: The data is not compatible with any member of the union (at $)
```

If members cannot be distinguished — same fields, no usable tag — `structure` raises `AmbiguousUnion` at conversion time.

If you need to implement your own discrimination strategy, you can write a hook matching the union.

```python
@register
def structure_hook(ctx: Ctx[Event], data: dict) -> Event:
    ...
```

### Thread safety

Scoped hooks are also the mechanism for thread safety: use a separate dispatcher per thread via `register.copy()` and `ctxure_config`.

A dispatcher can run only one `structure` or `unstructure` call at a time. Calling `structure` or `unstructure` again from inside a hook raises `ReentranceError`. Inside hooks, use `structure_default`, `unstructure_default`, `structure_by_type`, or `unstructure_by_type` to delegate to Ctxure.

```python
from threading import Thread

@register
def structure_hook(ctx: Ctx[Employee], data: str) -> Employee:
    name, department = parse_employee(data)
    return Employee(name, department)

def run_in_thread(record: str, out: list[Employee]) -> None:
    thread_register = register.copy()
    with ctxure_config(dispatcher=thread_register):
        out.append(structure(Employee, record))

employees = []
threads = [
    Thread(target=run_in_thread, args=("jack@data", employees)),
    Thread(target=run_in_thread, args=("jane@sales", employees)),
]

for thread in threads:
    thread.start()
for thread in threads:
    thread.join()
```

### General Multiple Dispatch

Ctxure's hook system is built on top of its own internal [multiple dispatch](https://en.wikipedia.org/wiki/Multiple_dispatch) system. You don't need prior knowledge of multiple dispatch to use Ctxure — the `ctxure.register` decorator covers everyday hook registration. However, the multiple dispatch system can also be used as a general-purpose dispatcher beyond Ctxure's hooks.
See [Multiple Dispatch](#multiple-dispatch) for details.

```python
from dataclasses import dataclass
from typing import Literal

from ctxure import Ctx, register, structure

@dataclass
class Espresso:
    shots: int

@dataclass
class Latte:
    shots: int

@dataclass
class Americano:
    shots: int

@dataclass
class Mocha:
    shots: int

Drink = Latte | Americano | Mocha

# General multiple dispatch: (Espresso, add-in tag) → specific drink
@register
def brew(base: Espresso, add: Literal["milk"]) -> Latte:
    return Latte(base.shots)

@register
def brew(base: Espresso, add: Literal["water"]) -> Americano:
    return Americano(base.shots)

@register
def brew(base: Espresso, add: Literal["chocolate"]) -> Mocha:
    return Mocha(base.shots)

# Ctxure hook: delegate pairing logic to brew
@register
def structure_hook(ctx: Ctx[Drink], data: dict) -> Drink:
    base = structure(Espresso, data["base"])
    return brew(base, data["add"])

structure(Drink, {"base": {"shots": 2}, "add": "milk"})       # Latte(shots=2)
structure(Drink, {"base": {"shots": 1}, "add": "chocolate"})  # Mocha(shots=1)
structure(Drink, {"base": {"shots": 3}, "add": "water"})      # Americano(shots=3)
```

## Default behavior

### structure

```python
structure(target_type, data, extra=None)
```

- `target_type`: The type of the structured data.
- `data`: The data to be structured.
- `extra`: Extra data to be used by user-defined hooks. See also [Injecting extra data](#injecting-extra-data).

If `target_type` is `Any`, the default handler returns `data` as-is. The same applies to any field or element declared as `Any`. However, hook dispatch still runs at those positions. Hooks matching on owner type (`Of`), root type (`Under`), or path can fire regardless of the `Any` declaration.

#### Target types supported by default

Note that these are target types (the `target_type` argument or declared types of fields/elements), not source data types.

Scalar types

- `bool`, `int`, `float`, `str`:
    - If the input is the same type, returned as-is.
    - If the input is a subtype, converted to the target type. Note that `bool`, `int`, `float` are treated as forming a subtype hierarchy, even though `issubclass(int, float)` returns `False`.
    - `int` to `bool` coercion is supported.
    - No coercion to `str`. You need to explicitly write a hook to convert strings to numbers or vice versa.
- `Enum`:
    - Conversion from any value matching an `Enum` member's `.value`. Raises `ValidationError` if no member matches.
- `Decimal`:
    - Conversion from `str`.
    - Note that conversion from `int` or `float` is not supported by default. Register a hook if needed.
- `bytes`:
    - Conversion from base64 encoded `str`.
- `Path`:
    - Conversion from `str`.
- `UUID`:
    - Conversion from `str`.
- `date`, `datetime`:
    - Conversion from ISO-format `str`.

Composite types

- `list[T]`, `set[T]`, `frozenset[T]`, `Sequence[T]`, `Collection[T]`:
    - Conversion from any of `list`, `tuple`, `set`, `frozenset` to any of them is supported. `Sequence[T]` and `Collection[T]` targets produce a `list`.
    - Elements are converted with `T` as target type. Conversion from `list` and `tuple` preserves the index.
    - For bare collection types (e.g., `list`), the element type is regarded as `Any`.
- `tuple[T1, T2, ...]`:
    - Fixed-length tuple with one declared type per position. Each position is converted by its declared type.
    - The variadic form `tuple[T, ...]` (and bare `tuple`) is treated homogeneously, with all elements converted as `T` (or `Any` for bare).
- `dict[K, V]`:
    - Conversion from `dict` is supported. Both key and value are converted.
    - `dict` is regarded as `dict[Any, Any]`. The single-arg `dict[K]` is not supported.
- `TypedDict`:
    - Conversion from `dict` is supported.
    - Each declared field is converted from the source value of the same key, according to declared types.
    - Optionality follows `total=` and `Required[]` / `NotRequired[]`. Missing required keys raise `MissingFields`.
    - PEP 728 (planned for Python 3.15, available via `typing_extensions`): with `closed=True`, extra keys raise `ExtraFields`. With `extra_items=T`, extra keys are kept and each value is structured as `T`. Otherwise (the default), extra keys are silently dropped. `closed` / `extra_items` declared on an ancestor TypedDict is inherited.
- Dataclass:
    - Conversion from `dict` is supported.
    - Each declared field is converted from the source value of the same key, according to declared types.
    - Default value and factory are supported.
    - If source `dict` is missing required fields or has extra fields, `MissingFields` or `ExtraFields` is raised. This is stricter than `TypedDict`'s default, which drops extras silently.

Derived types

- Union:
    - Any union of the supported types is also supported as a target type.
    - Dataclasses and `TypedDicts` are discriminated by the source `dict`'s field set and/or by `Literal[<single_value>]` tag fields with distinct values (tagged union); the two mechanisms compose, so different subsets may be split by different tag fields. The source `dict` must carry any tag that's used, even if the Python-side field has a default. If the members cannot be distinguished, `AmbiguousUnion` is raised. See [Union discrimination](#union-discrimination) for examples.
    - For other types, the member is selected by the following priority. At each step, a member is only eligible if it is constructable from the data — i.e., a hook or default handler exists for the data's runtime type and the member type. (1) If a user-registered hook matches exactly one member for the data's runtime type, that member is selected. (2) Otherwise, if the data's runtime type matches exactly one member, that member is selected. See [Restrictions on `data` type](#restrictions-on-data-type) for some caveats on the match. (3) Otherwise, the member is selected by checking whether a default handler is registered for the member and the data's runtime type; if exactly one matches, it is selected. If at any step multiple eligible candidates remain, `AmbiguousUnion` is raised.
    - The discriminated member becomes the dispatch target, so a hook registered for the current context (the discriminated member type, owner, root, path) fires as usual.
    - If you need custom union resolution, you can register a hook for the union type. See [Hook resolution](#hook-resolution) for details.
- `Literal`:
    - Accepts only values equal to one of the declared literal constants. Types also should be identical, for example, `Literal[0]` does not accept `False`. The accepted value is returned as-is. Raises `ValidationError` otherwise.
    - `Literal[a, b, ···]` is equivalent to `Literal[a] | Literal[b] | ···`.
    - A hook on `Ctx[int]` will not catch `Literal[1]`; register for `Ctx[Literal[1]]` instead.
- `NewType`:
    - Default handler for the supertype is called. For example, `Int = NewType("Int", int)` is treated as target type `int`. However, a hook for `int` does not fire unless it is registered with `@register.ctx_subtypes`. You can register a hook with `Ctx[Int]`. The hook fires only for `Int`, not `int`.
- Type alias:
    - `type X = Y` is regarded as transparent aliasing. `X` is exactly the same as `Y`.


### unstructure

```python
unstructure(declared_type, data, extra=None)
```

- `declared_type`: The type of the structured data.
- `data`: The data to be unstructured.
- `extra`: Extra data to be used by user-defined hooks. See also [Injecting extra data](#injecting-extra-data).

`declared_type` is respected — not the runtime type of `data`. For example, let `derived` be an instance of `Derived`, a subclass of `Base`. `unstructure(Base, derived)` drops any fields that `Derived` adds beyond `Base`. The same "slicing" happens when the declared type of a field or element is `Base` but the runtime value is `Derived`.

Another example is the union discrimination. When the declared type is a union, a single member is discriminated because one specific declared type is needed for hook resolution and recursive unstructuring of fields or elements.

This is important also for hook resolution. Let's suppose that `Foo` is a `TypedDict` class. You can register two hooks `unstructure_hook(ctx: Ctx[Foo], data: dict)` and `unstructure_hook(ctx: Ctx[dict], data: dict)`. If the current data is declared as `Foo` (e.g., a field declared as `Foo` or an element of `list[Foo]`), the former hook fires. If the current data is declared as `dict`, the latter hook fires.

Unlike `structure`, `unstructure` does not verify `data` against `declared_type` — it follows the declared shape and reads only what that shape calls for. For instance, `closed=True` on a `TypedDict` raises on `structure` but is a no-op on `unstructure` (extras are simply not emitted). However, it assumes the runtime type is compatible with the declared type. If the runtime type of a data is not compatible to its declared type (e.g., `float` value assigned to a field declared as `int`), the default behavior is not defined.

If the declared type is `Any`, however, Ctxure respects the runtime type. For example, `unstructure(Any, derived)` includes all of `derived`'s fields in the result. `Any` is propagated to children, so they are unstructured as `Any` too. Note that user hooks registered against specific target types do not fire at `Any`-typed positions; only `Ctx[Any]` hooks (and hooks matching by owner type, root type, or path) match.

#### Declared types supported by default

The defaults broadly mirror the structure side, applied in reverse. Again note that these are declared types (the `declared_type` argument or declared types of fields/elements), not source data types.

Scalar types

- `bool`, `int`, `float`, `str`:
    - Returned as-is when the runtime type matches.
    - Subtypes are converted upward in the same hierarchy as `structure` (`bool → int → float`). For example, `unstructure(int, True)` returns `1`.
- `Enum`:
    - Unstructured as the member's `.value`. When used as a `dict` key, stringified to `str(member.value)`.
- `Decimal`, `Path`, `UUID`:
    - `str(value)`.
- `bytes`:
    - base64-encoded `str`.
- `date`, `datetime`:
    - ISO-format `str` via `.isoformat()`.

Composite types

- `list[T]`, `set[T]`, `frozenset[T]`, `Sequence[T]`:
    - Unstructured to `list`. Elements are unstructured as `T`. For bare types (e.g., `list`), elements are unstructured as `Any`.
- `tuple[T1, T2, ...]`:
    - Fixed-length tuple with one declared type per position. Unstructured to `list`; each position is unstructured by its declared type.
    - The variadic form `tuple[T, ...]` (and bare `tuple`) is treated homogeneously, with all elements unstructured as `T` (or `Any` for bare).
- `dict[K, V]`:
    - Unstructured to `dict`. Each key is unstructured first; the result must be `str`, otherwise `ValidationError` is raised. Integer and `Enum` keys are stringified automatically.
- `TypedDict`:
    - Unstructured to `dict`. Each declared field is unstructured according to its declared type.
    - With `extra_items=T`, extra runtime keys are kept and unstructured as `T`. Otherwise extra runtime keys are silently dropped.
- Dataclass:
    - Unstructured to `dict`. Each declared field is unstructured. Slicing applies as described above.

Derived types

- Union:
    - `TypedDict`s in the union are discriminated the same way as in `structure` — by field set and/or `Literal[<single_value>]` tag fields (tagged union).
    - For non-`TypedDict` members, the matching member is selected by the same runtime-type and constructability rules used for non-dataclass unions in `structure`. Dataclasses are also selected by runtime type.
    - Ambiguity raises `AmbiguousUnion`.
    - The selected member becomes the dispatch target, so a hook registered on the member type fires as usual.
- `Literal`:
    - The default handler unstructures the value by its runtime type (e.g., `Literal[1, 2]` → `int`, `Literal["a", "b"]` → `str`), without verifying that the value belongs to the literal set. Register a hook for `Ctx[Literal[...]]` to override.
- `NewType`:
    - Unstructured as the supertype. A hook for the supertype does not fire unless it is registered with `@register.ctx_subtypes`.
- Type alias:
    - `type X = Y` is transparent; `X` is exactly the same as `Y`.

When the declared type is `Any`, the runtime type drives dispatch and `Any` is propagated to children:

- Primitives are returned as-is.
- `Path`, `UUID`, `Decimal`: `str(value)`.
- `bytes`: base64-encoded `str`.
- `date`, `datetime`: ISO-format `str`.
- Lists, tuples, sets, frozensets, dicts, and dataclass instances are recursed into; each child carries `Any`.

## Defining hooks

Ctxure first tries to apply a hook for the current context and data. If no hook matches the current context and data, it tries a default handler. So, a hook can override the default behavior or coexist with defaults.

Hook names are fixed as `structure_hook` and `unstructure_hook`. You cannot use arbitrary names.

The hook signature declares when the hook should fire (if it wins the competition with other hooks), not what context information it is interested in. The `ctx` argument always carries full context information. See [Ctx] for the available information.

### structure_hook

```python
from ctxure import register, Ctx

@register
def structure_hook(ctx: Ctx[...], data: T):
    ...
```

This defines a structure hook converting an input value of type `T`.

The `Ctx` type declares in which context this hook fires. The context is a position in the (output) structured object graph, not in the (input) unstructured object graph. See [Context](#context) and [Hook resolution](#hook-resolution). You can set the return type but it is not used by Ctxure. Note that you cannot use an arbitrary function name; it must be `structure_hook`.

`T` can be a union, Literal, type alias, user-defined (fully parameterized) generic type, **bare** built-in collection type (like `list`, `set`, ...), or built-in collection type parameterized with `Any` (like `list[Any]`, `set[Any]`, ...). See [Restrictions on `data` type](#restrictions-on-data-type) for why parameterized built-in collections (like `list[int]`), types defined with `NewType`, and `TypedDict` classes are not supported as a `data` type hint.

### unstructure_hook

```python
from ctxure import register, Ctx

@register
def unstructure_hook(ctx: Ctx[...], data: T):
    ...
```

This defines an unstructure hook converting an input value of type `T`. Almost the same as `structure_hook` except that `unstructure_hook` is fired during unstructuring.

### Manual delegation

Utility to call default handlers or other hooks manually.

**structure_default(ctx, data, keymap=None) / unstructure_default(ctx, data, keymap=None)**:

Call the default handler, bypassing any hook. Note that hooks are not bypassed for fields or elements of `data`. See [Pre- and post-validation](#pre--and-post-validation) for an example.

`keymap: dict[str, str | KeyPath]` is used to map field names to dict keys for dataclasses or `TypedDict`. A `str` value is one dict key. A `KeyPath` value is a nested location, relative to `data`; `structure_default` supports it, while `unstructure_default` supports only single-key `KeyPath`s for now (see [Nested keys](#nested-keys)). Any other value type for a field of the target raises `ValidationError`. `keymap` can contain only renamed fields. `keymap=None` means that all field names are identical to the dict keys. For `structure_default`, the input `dict` must use the mapped key. For `unstructure_default`, the output dict carries the mapped key. Two fields mapped to the same key raise `ValidationError` in `unstructure_default`, since one would overwrite the other. In either case, the original field name is not used. `keymap` should be defined as a module-level constant and not be mutated. A local variable creates a new dict object on every call, defeating the internal cache. `keymap` is used only for structuring or unstructuring dataclasses and `TypedDict`s. For other non-union types, it is ignored. Passing `keymap` to default conversion for a union raises `ValidationError`; register a hook for the concrete member type instead. See [Renamed fields](#renamed-fields) for an example.

**structure_by_type(ctx, data) / unstructure_by_type(ctx, data)**:

Call the default handler or hooks registered with only the target type. Hooks requiring root type, owner type, or path conditions are ignored for the current position. For fields or elements within the current value, the owner type is available, but root type and path remain suppressed. This is useful when a more-specific hook (one with `Under`, `Of`, or a path) needs to delegate to the less-specific hook or built-in default for the same type, then adjust the result. See [Root type](#root-type) for an example.

We can also call `structure` or `unstructure` with a different target type or modified `data`. However, this starts a completely new conversion. The current context information is ignored in this nested conversion.


## Context

### Ctx

`Ctx` accepts the following type parameters. When multiple parameters are given, all of them must match the context for a hook to fire.

- **Type**: The target type, e.g., the declared type of a dataclass field when structuring it from a dict value. `Literal`, `NewType`, and unions are also allowed.
- **Root type**: `Under[T]` means the type passed to `structure` or `unstructure` at the top of the current conversion. Lets a hook fire only when the conversion was entered at a specific type. See [Root type](#root-type) example.
- **Owner type**: `Of[T]` means the type of the owner (parent, container) of the current value.
- **Path expression**: A string describing the position in the structured object graph. See [Path expression](#path-expression).

An instance `ctx` of type `Ctx` has the following properties.

- **structured_type**: The target type.
- **structured_key**: Identifier of the current value within its owner. The concrete type depends on the owner:
    - `dataclasses.Field` instance for a dataclass field.
    - Field name (string) for a `TypedDict` field.
    - Integer index for a `Sequence`.
    - Key (any hashable type) for a `dict` value.
    - `None` for the root context or a `set`/`frozenset` element.
- **structured_path**: The current path in the structured data graph.
- **unstructured_path**: The current path in the unstructured data graph.
- **parent**: The parent context. For example, if the current context is an element of a list, `ctx.parent` is the context of that list. `None` for the root context.

The two properties below are aliases that return `structured_key` as-is, with narrower declared return types to give type checkers and IDEs better hints. No conversion or validation occurs — calling them on the wrong kind of context returns whatever `structured_key` happens to hold.

- **field**: typed as `dataclasses.Field`. Use on dataclass-field contexts.
- **index**: typed as `int`. Use on sequence-item contexts.

The current value and the `extra` argument are accessed via helper functions.

- **get_data(ctx)**: The current value being processed. This duplicates the hook's `data` argument, but it is useful for navigating parent or sibling data via `get_data(ctx.parent)`.
- **get_extra(ctx)**: The `extra` argument passed to `structure` or `unstructure`.
- **get_root(ctx)**: The root context.
- **get_parent(ctx)**: The same as `ctx.parent`.

## Hook resolution

### Matching with subtype relations

**`ctx: Ctx[T]` matches only `T` exactly. Subtypes of `T` do not match.** For example,
- A structure hook with `Ctx[date]` does not fire when Ctxure structures a field or element declared as `datetime`.
- A structure hook with `Ctx[int | str]` does not fire when Ctxure structures a field or element declared as `int` or `str`. It fires only when the field or element is declared as `int | str`.
- A structure hook with `Ctx[Literal[1, 2]]` does not fire when Ctxure structures a field or element declared as `Literal[1]` or `Literal[2]`. It fires only when the field or element is declared as `Literal[1, 2]` or `Literal[1] | Literal[2]`.
- A structure hook with `Ctx[int]` does not fire when Ctxure structures a field or element declared as `MyInt = NewType("MyInt", int)`. It fires only when the field or element is declared as `MyInt`.
- A structure hook with `Ctx[int]` does not fire when Ctxure structures a field or element declared as `Literal[1]`.
- A structure hook with `Ctx[Foo[date]]` does not fire when Ctxure structures a field or element declared as `Foo[datetime]`.
- A structure hook with `Ctx[Foo[Any]]` or `Ctx[Foo]` *fires* when Ctxure structures a field or element declared as `Foo[str]`, `Foo[Any]` or `Foo`. `Any` used as a type parameter acts as a wildcard in exact match.

**`data: T` matches `T` and any subtype of `T`.** For example,
- A structure hook with `data: date` accepts a `datetime` instance.

**The `register.ctx_subtypes` decorator widens `ctx` matching to subtypes.** For example,
- A structure hook with `Ctx[date]` registered via `register.ctx_subtypes` fires when Ctxure structures a field declared as `datetime`.
- A structure hook with `Ctx[int | str]` registered via `register.ctx_subtypes` fires when Ctxure structures a field declared as `int` or `str`.
- A structure hook with `Ctx[Literal[1, 2]]` registered via `register.ctx_subtypes` fires when Ctxure structures a field declared as `Literal[1]` or `Literal[2]`.
- A structure hook with `Ctx[int]` registered via `register.ctx_subtypes` fires when Ctxure structures a field or element declared as `MyInt = NewType("MyInt", int)`.
- A structure hook with `Ctx[int]` registered via `register.ctx_subtypes` fires when Ctxure structures a field declared as `Literal[1]` or `Literal[2]`.
- A structure hook with `Ctx[Foo[date]]` registered via `register.ctx_subtypes` fires when Ctxure structures a field or element declared as `Foo[datetime]`.
- Exact match has higher priority. If a context matches both an exact hook and a subtype hook, the exact one wins.

**Some notes on subtype relations**

For both `ctx` and `data`, any subtype relation between generic types is assumed to be covariant. For example, `list[datetime]` is treated as a subtype of `list[date]`, even though `list` is actually invariant.

Ctxure regards `int` as a subtype of `float` and `float` as a subtype of `complex`, even though `issubclass` returns `False` for these pairs.

### Conflict resolution

What happens if the current context matches multiple hooks? In short, the most specific one wins. `ctx` takes priority and `data` is secondary.

- There is no priority among the four "axes" (target type, root type, owner type, and path).
    - `Ctx[int]`, `Ctx[Under[Foo]]`, `Ctx[Of[Foo]]`, and `Ctx[".foo"]` are not comparable.
- *Additionally* specified axes are considered more specific.
    - `Ctx[".foo", Of[Foo]]` is more specific than `Ctx[".foo"]` or `Ctx[Of[Foo]]`.
    - `Ctx[Employee, Under[PublicReport]]` is more specific than `Ctx[Employee]` or `Ctx[Under[PublicReport]]`.
    - However, `Ctx[int]` and `Ctx[".foo", Of[Foo]]` are not comparable. If a context matches both, Ctxure raises an exception during structure or unstructure.
- Within each axis:
    - Types can be compared. This only matters when some hooks are registered with `register.ctx_subtypes`.
        - The notion of "more specific type" is intuitive but not simple to formalize. The examples below should be sufficient; see [doc/multidispatch_spec.md](doc/multidispatch_spec.md) for the precise spec.
        - `int` wins over `float`.
        - `int` wins over `int | str`.
        - `int | str` wins over `int | str | date`.
        - `Literal[1, 2]` wins over `Literal[1, 2, 3]`.
        - `list[int]` wins over `list[float]`.
        - `list[int]` wins over `list` or `list[Any]`.
        - `int` and `str` cannot match the same context, so they are not comparable.
    - `Of[S]` is more specific than `Of[T]` when `S` is more specific than `T`. This only matters when some hooks are registered with `register.ctx_subtypes`.
    - `Under[S]` is more specific than `Under[T]` when `S` is more specific than `T`. Same caveat as `Of`.
    - A path `S` is more specific than another path `T` if `T` can be obtained from `S` by replacing some parts with the wildcard `?`. A rootless path is treated as a rooted path whose leading prefix is a multi-level wildcard.
        - `"$.foo[0]"` is more specific than `"$.foo[?]"`.
        - `"$.foo"` is more specific than `".foo"`.
        - `"$.foo"` and `"$.foo.bar"` cannot match the same context, so they are not comparable.
- A more specific `data` type wins over a less specific one. `data` is consulted only when `ctx` types tie or are incomparable. For example, if `Ctx[int | str]` and `Ctx[int | date]` are registered with `ctx_subtypes` and both match a target type `int`, the type of `data` is consulted.
- If the resolution rule fails to single out a hook, `MultipleStructureHooks` or `MultipleUnstructureHooks` is raised.

Note that hook registration order has no effect on resolution. If multiple hooks with the exact same signature are registered, the last one overrides the others.

See [doc/multidispatch_spec.md](doc/multidispatch_spec.md) for more details.

## Restrictions on `data` type

Some types cannot be used as a `data` type hint in `structure`, `unstructure`, `structure_hook`, and `unstructure_hook` due to Python's limited runtime type information. Ctxure raises a `TypeError` when a hook with such a `data` hint is registered.

- Python built-in generic containers in parameterized form are not allowed.
- Generic classes with `__slots__` are not allowed.
- Generic dataclasses with `slots=True` or `frozen=True` are not allowed.
- Types defined with `NewType` are not allowed.
- `TypedDict` classes are not allowed.

For disallowed generic types, the bare type or parameterization with `Any` is allowed instead. For example, `list` or `list[Any]` are allowed, while `list[int]` is not.

These types can still appear as type parameters. For example, they can be a type parameter of `Ctx` or of a user-defined generic class used as the `data` hint. They are disallowed only as a direct top-level `data` hint.

The following explains why they are not allowed.

### Restricted generic types

`ctx: Ctx[list[int]]` is fine. `data: Foo[list[int]]` is also fine. However, `data: list[int]` is not — this raises a `TypeError` at hook registration time.

Python's built-in containers do not carry runtime generic type information. Ctxure has no reliable way to determine whether `[1, 2, 3]` is a `list[int]` at runtime. Doing so would require inspecting every element, which is expensive. Even then, only compatibility can be established, not identity — `[1, 2, 3]` could be `list[complex]` or `list[object]`. A later value at the same context could be `[1, 2.2, 3j, "a"]`. This ambiguity would break hook resolution caching.
For these reasons, Ctxure rejects hooks with `data: list[int]`.

Slotted generic classes and frozen dataclasses have the same issue. They also don't carry runtime generic type information.

More technically, Ctxure relies on the `__orig_class__` attribute to get the parameterization of an instance. These types don't carry `__orig_class__`.

### NewTypes and TypedDicts

`NewType` has the same restriction. It is fine as a parameter of `Ctx` or as a type parameter of a user-defined generic type used as the `data` hint. But it cannot be used as a top-level `data` hint. An instance of a `NewType` carries no relevant runtime type information — for example, `NewType("Int", int)(1)` is just `1` of type `int`.

`TypedDict` has the same restriction. `data: MyTypedDict` is not allowed. Instances of a `TypedDict` are plain `dict` objects at runtime, not the `TypedDict` class. Use `data: dict` instead.

### Note on user-defined generic classes

User-defined generic classes work anywhere. Note that Ctxure does not infer runtime generic type parameters — *you must explicitly parameterize a generic class.* For example:

```python
@dataclass
class Foo[T]:
    foo: T

@register
def structure_hook(ctx: Ctx[str], data: Foo[list[int]]) -> str:
    ...

# The hook fires.
structure(str, Foo[list[int]]([1, 2]))

# Invalid data type. Anyway the hook fires.
structure(str, Foo[list[int]](["a", "b"]))

# Caution: The hook does not fire. NoStructureHook error.
structure(str, Foo([1, 2]))
```

## Configuration

`ctxure.ctxure_config` is a context manager to control the overall behavior of ctxure. Currently it provides only one option, `dispatcher`. See [Scoped hooks](#scoped-hooks).


## Path expression

Note that in `Ctx`, the path expression refers to a location in structured data, not unstructured data.

### Field

- `".foo"`: field named `foo` of a dataclass or a `TypedDict`.
- `".foo-bar"`: field named `foo-bar` of a `TypedDict`.
- `".'foo bar'"`: field named `foo bar` of a `TypedDict`.
- `".?"`: any field of a dataclass or a `TypedDict`.

A dataclass field name must be a valid Python identifier, while a `TypedDict` field name can be any string. Field expressions that are not plain identifiers or kebab-case names must be enclosed in quotation marks (`"` or `'`).

### Item

Here an item is an element of a `Sequence` accessed by integer index, or a value in a `dict`.

- `"[0]"`, `"[1]"`, ...: the element at index 0, 1, ... of a list, tuple, or other `Sequence`, or the value at integer key 0, 1, ... in a `dict`.
- `"['foo']"`: the value at string key `"foo"` in a `dict`.
- `"[Foo.A]"`: the value at `Enum` key `Foo.A` in a `dict`.
- `"[?]"`: any item.

Note that the `Enum` key `Foo.A` matches any `Enum` named `Foo` regardless of which module defines it.

### Dict key

These match the keys themselves, not the values they index.

- `"[~0]"`, `"[~1]"`, ...: integer dict key.
- `"[~'foo']"`: string dict key `"foo"`.
- `"[~Foo.A]"`: `Enum` dict key `Foo.A`.
- `"[~?]"`: any dict key.

`"[~0]"`, `"[~1]"`, ... do not represent indices of a sequential container. The note on `Enum` in the previous section also applies here.

Note that during `structure`, when Ctxure converts an unstructured dict key into the structured key, the structured key does not exist yet. As a result, only `"[~?]"` can match — a specific dict-key path cannot. Thus Ctxure raises a `TypeError` when a `structure_hook` with a specific dict-key path is registered.
By contrast, when `structure` converts a dict value, the structured key has already been produced (Ctxure converts the key before the value), so a specific item path like `"['foo']"` can match.
During `unstructure`, the structured dict key always exists, so a specific dict-key path can match.

### Path

The above expressions can be composed into a path starting with the root marker `"$"`.
For example, `"$.foo[0].?[?]"` means
- any item of
    - any field of
        - the first item of
            - the `foo` field of
                - the root.

The wildcard `"?"` does not span multiple levels.

Rootless expressions (those without a leading `"$"`) are always single-segment — a bare field expression like `".foo"` or a bare item expression like `"[?]"`. Multi-segment paths must be rooted, i.e., start with `"$"`. For example, `"$.foo[?]"` is valid, but `".foo[?]"` is not.

### Anything

- `"?"` or `Any`: anything.

Technically `"?"` is a location constraint and `Any` is a type constraint, but either alone is equivalent to "anything" — `Ctx["?"]` and `Ctx[Any]` produce the same context type.

## Error

All exceptions raised by Ctxure inherit from `ctxure.CtxureError`. Catch that to handle any Ctxure-raised failure uniformly.

```
CtxureError
├── NoStructureHook
├── NoUnstructureHook
├── MultipleStructureHooks
├── MultipleUnstructureHooks
├── AmbiguousUnion
├── ReentranceError
└── ValidationError
    ├── MissingFields
    └── ExtraFields
```

- **NoStructureHook / NoUnstructureHook** — no hook (user-registered or default) matched the current target type and data type.
- **MultipleStructureHooks / MultipleUnstructureHooks** — more than one hook matched and the conflict resolution rules couldn't single one out. See [Conflict resolution](#conflict-resolution).
- **ValidationError** — raised by hooks (including built-ins) to signal that the data is invalid for the target type. Hook authors typically raise this directly: `raise ValidationError(ctx, data, "...")`.
- **MissingFields / ExtraFields** — specializations of `ValidationError` raised by the default dataclass / TypedDict handlers when required fields are absent or unexpected keys are present.
- **AmbiguousUnion** — union dispatch could not pick a single candidate (either probing matched several, or the chosen members are indistinguishable).
- **ReentranceError** — raised when `structure` or `unstructure` is called while another conversion is already running on the same dispatcher.


Every Ctxure error exposes these attributes:

- `ctx` — the `Ctx` at which the error was raised. `ctx.structured_path` is included in the default message; use `ctx.unstructured_path`, `ctx.structured_type`, `ctx.parent`, `get_extra(ctx)`, etc. for richer inspection.
- `data` — the data value that triggered the error.

Specific errors carry extra information:

- `candidates` on `MultipleStructureHooks` and `MultipleUnstructureHooks` — the list of competing `Method`s; the default message includes their signatures and source locations.
- `missing` on `MissingFields` — list of required field names that were absent.
- `extra` on `ExtraFields` — list of unexpected key names that were present.


## Multiple Dispatch

This section explains the multiple dispatch system underlying Ctxure's hook system. You can skip it if you are not interested in general multiple dispatch — you do not need to know about it to use Ctxure. That said, the system can also be used for general-purpose dispatching outside of Ctxure's hooks.

If you are unfamiliar with the term "multiple dispatch" but have experience with languages that support "overloading", think of it as overloading dispatched by argument types at runtime rather than at compile time.

```python
from ctxure import register

@register
def foo(a: int) -> str:
    return "int"

@register
def foo(a: float) -> str:
    return "float"

@register
def foo(a: int, b: float) -> str:
    return "int, float"

foo(1)  # 'int'
foo(1.0)  # 'float'
foo(1, 1.0)  # 'int, float'

a: float = 1
foo(a)  # 'int', by the runtime type `int` rather than the static type `float`.
```

To create a new dispatcher without Ctxure's default handlers, use the `@ctxure.multidispatch.dispatch` decorator, or create a new instance of `ctxure.multidispatch.Dispatch` and use it as a decorator.

There are other Python multiple dispatch libraries like [plum](https://github.com/beartype/plum) or [multimethod](https://github.com/coady/multimethod). Ctxure's system differs in a few ways.

- The dispatch resolution is lexicographic. Earlier (left) arguments are filtered first; ties at earlier positions can be broken by later ones.
- Arguments with default values are not allowed. Keyword-only arguments are allowed but are not used for dispatch resolution.
- The variance mode (covariance or invariance) can be declared per argument position. The default is invariant. Covariant positions are specified with the `@dispatch.covariant(*positions)` decorator, where `dispatch` is any instance of `ctxure.multidispatch.Dispatch`.
    - `Any` acts as a wildcard on the right-hand side of invariant subtype relations.
    - `Never` acts as a wildcard on the left-hand side of invariant subtype relations.
    - `@ctxure.register.ctx_subtypes` marks the specified parameterization of `CtxImpl[...]` (produced by `Ctx[...]`) as covariant. The default invariant mode of `Ctx` behaves like exact matching on `Ctx`'s type parameters.
- Virtual base classes: `DataClassBase`, `LiteralBase`, `NewTypeBase`, `TypedDictBase`, and `UnionBase`.
- No runtime generic type inference. Only explicit parameterization exposed via `__orig_class__` is recognized.

These design decisions are driven by Ctxure's requirements. Some aspects of Python's type system are deliberately respected while others are not, in order to keep the dispatch system's API and implementation practical.

See [doc/multidispatch_spec.md](doc/multidispatch_spec.md) for more details.


## Caveats

### Internal caching
Ctxure creates an internal converter for each root type when `structure` or `unstructure` is called with the type as the target or declared type for the first time. The first call is slow.
On subsequent calls for the same root type, the cached converter is reused and the call is much faster.
Any hook registration invalidates the converter cache.
When a dispatcher is copied, the converter cache is not copied. The copied dispatcher creates its own fresh converter cache.

### Thread safety
`structure` and `unstructure` are not thread-safe. For thread safety, use a separate dispatcher per thread. See [Scoped hooks](#scoped-hooks) for how to create an independent copy of the underlying dispatcher.

### `NewType` and `TypedDict` as `data` type
As explained in [Restrictions on `data` type](#restrictions-on-data-type), `NewType`s and `TypedDict`s are not allowed as the `data` type in a hook. In `unstructure` hooks it is easy to accidentally use them there, which causes a `TypeError` at hook registration.

### User-defined generic classes
Ctxure does not infer generic type parameters. You must explicitly parameterize a generic class. See [Note on user-defined generic classes](#note-on-user-defined-generic-classes).
