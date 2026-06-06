# Ctxure multidispatch system

Here we define a multidispatch system in Python. In the system, a user can declare each argument position of a function to be invariant or covariant to declare for which types of arguments the function should be dispatched.

The primary purpose of the dispatch system is to implement a serialization/deserialization library, called "ctxure" where default behavior and user-defined hooks are implemented over the multidispatch system. Roughly, the serialization/deserialization implementations have the signature `(ctx: Ctx[S], data: T)`. Here, for serialization $S$ is the declared type of `data` (e.g., the type of a dataclass field), and for deserialization $S$ is the target type to be constructed. `Ctx` has subclasses to represent various context in the target/data object graph.

We want the dispatch system to be useful for general purpose. However, if we need a design decision, the most important criterion is what is best for ctxure. Note also that we deliberately respect some aspects of Python's type system and ignore some other aspects to make the API and implementation of the dispatch system practical.


## About this document

This document defines the dispatch system precisely enough to implement and test. It combines three kinds of material:

- **Python background** — Standard Python type system concepts (e.g., `__orig_class__`, generic classes, parameterized types). The Preliminary section restates these for completeness.
- **Standard type theory** — Both subtype relations ($\preceq$ and $<:$) and the union/literal decomposition rules follow standard definitions. If you are familiar with subtyping in type systems, these may look familiar.
- **Our design decisions** — These are the parts that matter most for understanding this library:
    - `Any` (top) and `Never` (bottom) act as wildcards in invariant type parameter matching, via the $\simeq$ relation that recursively checks equality modulo `Never` on LHS and `Any` on RHS.
    - Variance is per argument position and hint of a method, not per type parameter of a generic type. A (hint, position) is fully covariant or fully invariant on all parameters.
    - `DataClassBase`, `TypedDictBase`, `LiteralBase`, `NewTypeBase` and `UnionBase` as virtual base classes that do not exist in Python's actual MRO.
    - `NewType` and built-in parameterized types are not supported as top-level method hints. They are supported only as type parameters.
    - `Literal` is supported as a top-level method hint via value-based promotion at call time. See the "Top-level Literal hints" section.
    - `int`, `float`, and `complex` form a subtype hierarchy.
    - The lexicographic, most-specific-match dispatch rule.


## Preliminary

First we define or clarify some terms. Any terms not described here should be interpreted with their standard meaning in Python's context.

- We distinguish a "generic class" and a "parameterized class". For example `list` is a generic class but not a parameterized class. `list[int]` is a parameterized (generic) class. A non-parameterized class means a non-generic class or a generic but not parameterized class. We do not consider partially parameterized types like `dict[str, T]`.
- We call a generic class a user-defined generic class if it provides `__orig_class__` instance attribute and `__orig_bases__` class attribute.
- We call a generic class a built-in generic class if it is not a user-defined generic class. Examples include `type`, `list`, `dict`, and `Sequence`.
- A union always has at least two elements. We don't regard a non-union hint as a single-element union.
- We'll define a class `UnionBase` as a virtual base of all unions. A union should not include `UnionBase` as a member.
- Let $S = T$ represent the standard equality between hints. This includes, for example,
    - `int` $=$ `int`
    - `list` $=$ `list`
    - `Literal[1, 2]` $=$ `Literal[2, 1]`
    - `int | str` $=$ `str | int`
    - `dict[int, str]` $=$ `dict[int, str]`
- Assume that $S$ and $T$ be classes and $S[U]$ extends $T[W]$ where $U = U_1, \ldots, U_n$ and $W = W_1, \ldots, W_m$ are, possibly empty, tuples of hints. Then $W_i$ is a type expression possibly involving some of $U_1, \ldots, U_n$. We denote $(W_1, \ldots, W_m)$ as `resolve_base_args(S, T, U)`. If $S[U]$ does not extend $T[W]$ for whatever $W$, `resolve_base_args(S, T, U)` $= \text{None}$. For variable-length tuples, we need some care. We have a specific section below on variable-length tuples. Here are examples.
    - `resolve_base_args(datetime, date, ()) = ()`
    - `resolve_base_args(str, int, ()) = None`
    - `resolve_base_args(list, Sequence, (int,)) = (int,)`
    - `resolve_base_args(list, list, (int,)) = (int,)`
    - Let `MyDict[T]` extend `dict[int, list[T]]`. Then `resolve_base_args(MyDict, dict, (str,)) = (int, list[str])`.
- We define a relation $\simeq$ for comparing type parameters in invariant context. It is equality extended with `Never` as a LHS wildcard and `Any` as a RHS wildcard, applied recursively through type parameters.
    - `Never` $\simeq T$ for any $T$.
    - $S \simeq$ `Any` for any $S$.
    - $S \simeq T$ if $S = T$ (for non-parameterized hints, including `Literal`s, unions, and `NewType`s).
    - $S[U] \simeq T[V]$ if `resolve_base_args(S, T, U)` $= W$ and $W_i \simeq V_i$ for each $i$.
- The system supports a plain class, user-defined generic class, built-in generic class, `NewType`, `Literal`, or union as a hint. In this doc, a hint always means one of these. Note that `NewType`, `Literal`, and union cannot be a runtime type of an object in Python, while they can be a hint, a type parameter of a generic type, or an element of a union.
- We consider all type parameters of a non-parameterized generic type as `Any` if we need to consider a non-parameterized generic class as a parameterized class. For example, `list` $=$ `list[Any]` and `list[list[Any]]` $=$ `list[list]`.


## Dispatch rule

The system maintains a set of _methods_ where each method has a signature $(T_1, \ldots, T_n)$ where $T_i$ is a plain class, a user-defined generic class, a built-in non-parameterized generic class, a `Literal`, a union of the foregoing, or `Any`. Different methods can have different $n$.

Each argument hint $T_i$ at position $i$ has an associated variance mode $m_{(T_i,\, i)}$, which can be _invariant_ or _covariant_ and governs which runtime types match $T_i$. We define the two modes in the following section. The variance mode is fixed per (position, hint) pair — neither position alone nor hint alone determines it: `list[int]` at position 0 and `list[str]` at position 0 may have different modes, and so may `list[int]` at position 0 and `list[int]` at position 1. Note that a generic type used as a hint must be fully parameterized; no generic methods are supported. This notion of variance differs from the standard meaning: standard variance is per type parameter of a generic type, whereas here it is per (position, hint) pair, and a hint at a given position is uniformly covariant or invariant on all its type parameters.

The system dispatches arguments $(v_1, \ldots, v_n)$ to a method. $v_i$ can be any runtime object, which includes a type object or a hint object (like `list[int]`, `int | str`).

The system does not support a built-in parameterized type or `NewType` as $T_i$. Python does not provide runtime type information on instances of these types, and inferring it is expensive and difficult to be correct. Note, however, that any hints can be used as a type parameter or an element of a union.

`Literal` is supported as $T_i$ via the value-based promotion mechanism described below. Other forms of value-based dispatch are not supported.

The "runtime type" of a value $v$ at argument position $i$ for a given multimethod $m$ is
- `Literal[v]` if $v$ matches a literal value registered at position $i$ of $m$ (see "Top-level Literal hints").
- otherwise `v.__orig_class__` if $v$ has `__orig_class__`.
- otherwise `type(v)`.

The dispatch rule:

- For an argument $v$ of runtime type $S$, a hint $T$, and a given subtype relation, we say $v$ matches $T$ if $S$ is a subtype of $T$.
- For an argument $v$ of runtime type $S$, a set of candidate hints $H = \{T_1, \ldots, T_n\}$ matched by $v$, and a subtype relation $m$, we say that $v$ matches $T \in H$ most specifically among the candidates according to the subtype relation $m$, if $T$ is subtype of every $T_i$.
- To dispatch arguments $(v_1, \ldots, v_n)$, the system tries to match the arguments to registered implementations lexicographically. All implementations accepting only $n$ arguments are the initial candidates.
    - For each argument position $i$, the system collects the hints $T_i$ of the current candidates that match $v_i$, then keeps only the most specific ones, each evaluated under the variance mode $m_{(T_i,\, i)}$ fixed for that (position, hint) pair. The methods behind the remaining hints become the candidates for the next position. If no hint matches, a `NoMatchFound` error is raised. Ties at one position may be broken by later positions.
    - If more than one method remains after the last position, a `MultipleMatchesFound` error is raised. Otherwise the single remaining method is called.


## Subtype relations

Here we define two subtype relations between type hints: invariant subtype relation $\preceq$ and covariant subtype relation $<:$ between type hints. The rules below are disjunctive: $S$ is a subtype of $T$ if any applicable rule establishes it. When a specific rule (e.g., for `UnionBase` or `DataClassBase`) and a general rule (e.g., union decomposition) could both apply, each is evaluated independently — a single matching rule is sufficient.

### Top type `Any`

`typing.Any` is the top type. For any type hint $S$ (including `Any`),

- $S \preceq$ `Any`
- $S <:$ `Any`

### Bottom type `Never`

`typing.Never` is the bottom type. For any type hint $T$ (including `Never`),

- `Never` $\preceq$ $T$.
- `Never` $<: T$.

### Subtype relation between classes

Let $S$ and $T$ be classes and `resolve_base_args(S, T, U)` $= W$, where $W$ is not None, and $V$ be a tuple of hints with $|W| = |V|$.

- $S[U] \preceq T[V]$ if $W_i \simeq V_i$ for each $i$.
- $S[U] <: T[V]$ if $W_i <: V_i$ for each $i$.

### Subtype relation with tuples

In this section, `...` in the middle of type variables, like `U_1, ..., U_n`, is not Python's `Ellipsis`. It means just omitted repetition.

For variable length homogeneous `tuple`s,

- `tuple[U, ...]` $\preceq$ `tuple[V, ...]` if $U \simeq V$.
- `tuple[U_1, ..., U_n]` $\preceq$ `tuple[V, ...]` if $U_i \simeq V$ for each $i$.
- `tuple[U, ...]` $<:$ `tuple[V, ...]` if $U <: V$.
- `tuple[U_1, ..., U_n]` $<:$ `tuple[V, ...]`, if $U_i <: V$ for each $i$.

Let `T` be a base of `tuple`, e.g., `Sequence` or `Iterable`.
- `tuple[U, ...]` $\preceq$ `T[V]` if $U \simeq V$.
- `tuple[U_1, ..., U_n]` $\preceq$ `T[V]` if $U_i \simeq V$ for each $i$.
- `tuple[()]` $\preceq$ `T[V]` for any `V`.
- `tuple[U, ...]` $<:$ `T[V]` if $U <: V$.
- `tuple[U_1, ..., U_n]` $<:$ `T[V]` if $U_i <: V$ for each $i$.
- `tuple[()]` $<:$ `T[V]` for any `V`.

Note that subtype relations between fixed length tuples are handled with the general definition between generic types.

Variable-length homogeneous tuples (`tuple[T, ...]` where `...` is Python's `Ellipsis`) are not considered parameterized classes for the purpose of `resolve_base_args` or the general class rules. They are handled exclusively by the rules in this section. Fixed-length tuples like `tuple[int, str]` are treated as parameterized classes with each element type as a type parameter, so `resolve_base_args(tuple, tuple, (int, str)) = (int, str)`.

### Subtype relation involving Literals

`Literal` is supported as a top-level method hint, including as a member of a top-level union.

When dispatching a value $v$ at argument position $i$, the runtime type of $v$ is `Literal[v]` if and only if $v$ is one of the literal values registered at position $i$ of that multimethod. The registered set covers both bare `Literal[...]` hints and `Literal[...]` members of a union. If $v$ is not among the registered literal values, the default runtime type rules apply.

Two values that compare equal but have different types, e.g., the integer `1` and the boolean `True`, are treated as distinct literals. A value registered as `Literal[1]` does not promote `True`, and vice versa.

Argument values that are not among the registered literal values at that position dispatch using the normal runtime type as if no `Literal` hint were present.

- `Literal[v_1, ..., v_n]` $<:$ `Literal[w_1, ..., w_m]` if $\{v_1, \ldots, v_n\} \subseteq \{w_1, \ldots, w_m\}$.
- `Literal[v_1, ..., v_n]` $<: T$ if `type(v_i)` is a subclass of $T$ for all $i$.
- `Literal[v_1, ..., v_n]` $\preceq$ `Literal[w_1, ..., w_m]` if $\{v_1, \ldots, v_n\} \subseteq \{w_1, \ldots, w_m\}$.
- `Literal[v_1, ..., v_n]` $\preceq T$ if `type(v_i)` $\preceq T$ for all $i$.

The $\preceq$ rules are needed because top-level `Literal` hints make `Literal[v]` appear in the LHS of $\preceq$ at runtime (via the value-based promotion described in the "Top-level Literal hints" section). Note that the $\preceq$ rules do not recurse through type parameters of the RHS — they always check the literal values against the RHS class directly. Inside nested type parameters of an invariant match, `Literal` is still compared via plain equality through $\simeq$.

We can derive the rules from rules for unions. However, we explicitly specify the rules for easier implementation.

### Subtype relation involving unions

We also define relations between unions. For arbitrary hints $A$, $B$, $A_i$, and $B_i$ which are neither unions nor `UnionBase`,

- $A \preceq B_1 \mid \ldots \mid B_n$ if $A \preceq B_i$ for some $i$.
- $A_1 \mid \ldots \mid A_n \preceq B$ if $A_i \preceq B$ for each $i$.
- $A_1 \mid \ldots \mid A_n \preceq B_1 \mid \ldots \mid B_m$ if for each $A_i$, there exists $B_j$ such that $A_i \preceq B_j$.
- $A <: B_1 \mid \ldots \mid B_m$ if $A <: B_i$ for some $i$.
- $A_1 \mid \ldots \mid A_n <: B$ if $A_i <: B$ for each $i$.
- $A_1 \mid \ldots \mid A_n <: B_1 \mid \ldots \mid B_m$ if for each $A_i$, there exists $B_j$ such that $A_i <: B_j$.

### Subtype relation involving NewTypes

Let $S$ be `NewType("S", T)` and $U$ be an arbitrary hint. Note that $T$ can be a parameterized class.

- $S <: U$ if $S = U$ or $T <: U$.

- We don't need $\preceq$ involving `NewType`s as `NewType`s don't appear as a type of a runtime argument nor appear as a top-level hint in a signature.

### Numeric tower

In Python, `int` is not a subtype of `float`. However, in practice, everyone assigns `int` value to a variable declared as `float`. PEP 484 explicitly declares `int` as compatible with `float` and `float` with `complex` for the purpose of type checking, so even type checkers allow such assignment. We explicitly define subtype relations between them to support such practice.

- `int` $\preceq$ `float` $\preceq$ `complex`.
- `int` $<:$ `float` $<:$ `complex`.

These subtype relations are transitive. Especially, `bool` is a subtype of `int` in Python, thus `bool` is a subtype of `float` and `complex` in both subtype relations.

### DataClassBase, TypedDictBase, LiteralBase, NewTypeBase, UnionBase

We define classes `DataClassBase`, `TypedDictBase`, `LiteralBase`, `NewTypeBase`, and `UnionBase` which act like abstract base classes of all dataclasses, `TypedDict`s, `Literal`s, `NewType`s, and unions, respectively.

- Let $S$ be a dataclass. `resolve_base_args(S, DataClassBase, U)` $= ()$ for any tuple of hints $U$.
- Let $S$ be a `TypedDict`. `resolve_base_args(S, TypedDictBase, U)` $= ()$ for any tuple of hints $U$.
- Let $S$ be a `Literal`, $S <:$ `LiteralBase`.
- Let $S$ be a `NewType`, $S <:$ `NewTypeBase`.
- Let $S$ be a union, $S <:$ `UnionBase`.
- `DataClassBase` is not a subclass of `DataClassBase` itself.
- `TypedDictBase` is not a subclass of `TypedDictBase` itself.
- `LiteralBase` is not a subclass of `LiteralBase`.
- `NewTypeBase` is not a subclass of `NewTypeBase`.
- `UnionBase` is not a subclass of `UnionBase`.
- These virtual bases classify the **outermost kind** of a type and are mutually exclusive for dispatch purposes. In particular, a union is not a subtype of `NewTypeBase` or `LiteralBase`, even if all its members are `NewType`s or `Literal`s — the general union decomposition rule (`union <: X` if all members `<: X`) does not apply when `X` is one of these virtual bases. A union's outermost kind is always "union", so it matches only `UnionBase` among the virtual bases.

We don't need to define $\preceq$ for them. `Literal`s, `NewType`s, `TypedDict`s and unions do not appear in the LHS of $\preceq$, so $\preceq$ involving these base classes does not occur.

### `TypedDict` is not a subtype of `dict`

A `TypedDict` class is not considered a subtype of `dict` for the purposes of $\preceq$ and $<:$ defined here. `TypedDict` classes relate only to other `TypedDict`s they inherit from, the universal top `object`, and the virtual `TypedDictBase`. Let $S$ be a `TypedDict`.

- NOT $S$ $\preceq$ `dict`
- NOT $S$ $<:$ `dict`

This rule keeps the ctxure hooks with `Ctx[TypedDict]` disjoint from hooks with `Ctx[dict]`. The runtime data side is unaffected: a `TypedDict` instance is still a plain `dict` at runtime.

### Notes on the rules

- The primary purpose of the variance concept is to ensure type safety in the standard type system theory. However, the variance rule in this doc is to dispatch function calls, not to ensure type safety. It is the user's responsibility to use the arguments in a type-consistent way.
- The standard definition of variance for subtype relation between parameterized classes is per type parameters. For example, $S[U, V]$ can be covariant on $U$ but invariant on $V$. However, our system does not allow this for practical brevity of dispatching. So an argument position is fully covariant on every parameter or fully invariant on every parameter.
- Note that `Any` $\preceq T$ and `Any` $<: T$ only when $T$ is `Any`. Especially `Any` $<:$ `object` is not true.
- A `NewType`, `TypedDict`, or union cannot be a type of a runtime value, thus they do not appear in the LHS of $\preceq$ or $<:$ in the multidispatch match. `Literal` likewise cannot be a runtime type of an arbitrary value, but the value-based promotion at top-level positions can introduce `Literal[v]` as the runtime type at that position; see "Top-level Literal hints". The definition of $<:$ recursively checks nested types with $<:$, so `NewType`, `TypedDict`, and union can also appear in the LHS of $<:$ in a nested context. For example, checking `Foo[int | str]` $<:$ `Foo[int | str | None]` needs checking `int | str` $<:$ `int | str | None`. The definition of $\preceq$ recursively checks $\simeq$, not $\preceq$, in type parameters. The $\simeq$ relation checks equality with `Never` and `Any` as wildcards, so `Literal`, `NewType`, `TypedDict`, or union can appear in a nested context of invariant match only via plain equality. `Any` and `Never` also cannot be a type of a runtime value. However, the rules in this doc allow them in the LHS of both subtype relations, as they are useful for finding "minimums" or "maximums" among registered methods. So,
  - In the LHS of $\preceq$, a plain class, a user-defined generic class, a non-parameterized built-in generic type, `Literal`, `Never`, or `Any` can appear.
  - In the LHS of $<:$, any hint can appear.
- We don't define contravariant subtype relation as we don't need it (at least for now).

## Note on the implementation

- The relations $\preceq$ and $<:$ are implemented by `ctxure.multidispatch._is_subtype_invariant` and `ctxure.multidispatch._is_subtype_covariant`
- The relation $\simeq$ is implemented by `ctxure.multidispatch._is_equal_invariant`. It builds on $=$ by adding `Never` as a LHS wildcard and `Any` as a RHS wildcard, and recursing through type parameters. The $=$ relation uses Python's `==` operator. Most hint objects support appropriate `==` operator. For example `int | str == str | int` is True and `Literal[1, 2] == Literal[2, 1]` is True. However, `==` does not support equivalence between bare generics and generics parameterized with `Any`. So we need `_equal_class`.
- The function `resolve_base_args` is implemented by `ctxure.typeutil._resolve_base_args`.
- We define `ctxure.typeutil.TypeInfo` and `ctxure.typeutil._type_info`, to provide simulated `__orig_bases__`, `__mro__`, and `__parameters__` for built-in generic types. It is to handle these problems.
  - Normalizing non-parameterized generic types with `Any` is tricky. For user-defined generic types we can get the number of type parameters with `__parameters__` or `__type_params__` attributes. However, for built-in generic types like `list` or `dict`, Python does not provide any API. Even writing `list[int, str]` does not raise any runtime error.
  - To implement the function `resolve_base_args`, we need to utilize `__mro__` and `__orig_bases__` of each type. Built-in generics usually don't have `__orig_bases__` and have an incomplete `__mro__`. For example, `list` does not have `__orig_bases__`, and its `__mro__` lacks `Sequence` or other `collections.abc` abstract classes.
- `DataClassBase`, `TypedDictBase`, `LiteralBase`, `NewTypeBase` and `UnionBase` need special handling as they are virtual and do not actually participate in `__mro__` or `__orig_bases__`.
- The literal interest set for top-level `Literal` hints is maintained on `ctxure.multidispatch.Multimethod` as `literal_interest` (per-position `dict[(type, value), Literal[v]]` with pre-built `Literal[v]` forms) and `literal_positions` (the tuple of positions whose interest set is non-empty). `Multimethod.__call__` uses `literal_positions` to gate the value-based promotion: when it is empty, the fast path is identical to the pre-Literal implementation; otherwise `_types_with_literals` does a per-position lookup. The interest set is updated by `register()` and copied by `copy()`.
- `TypedDict` classes do not support `issubclass()`. A `TypedDict`'s inheritance from other `TypedDict`s is recorded only in `__orig_bases__`; `__mro__` reflects only the `dict` / `object` tail, not the `TypedDict` parent chain. For example, given `class B(A)` where both are `TypedDict`s, `B.__mro__` is `(B, dict, object)` and `A` is reachable only through `B.__orig_bases__`. When `S` is a `TypedDict`, the implementation substitutes `issubclass(S, B)` with a recursive walk of `getattr(S, "__orig_bases__", ())` that returns True iff `B` is reachable. `object` is treated as the universal top in this walk (always reachable), since it is not in `__orig_bases__`. `dict` is not reached via this walk, enforcing `NOT S $<:$ dict` for `TypedDict` `S`.

