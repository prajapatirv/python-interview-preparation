"""
Plugin / extension architecture: three ways to let code be swapped or extended,
and the trade-off between them.

  1. decorator registry     — simple, but the module must be IMPORTED to register
  2. __init_subclass__      — registers automatically at class definition
  3. entry points           — a SEPARATE pip package can extend you

Run me: python 03_plugin_architecture.py
Deep dive: ../deep_dive/11_python_framework_development.md
"""
from abc import ABC, abstractmethod


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ================================================================== 1. registry
section("1. decorator registry — explicit, simple, opt-in per class")

_PLUGINS: dict[str, type] = {}


def register(name):
    def deco(cls):
        if name in _PLUGINS:
            raise ValueError(f"duplicate plugin name: {name!r}")
        _PLUGINS[name] = cls
        return cls                      # MUST return the class — forgetting this
    return deco                         # silently sets your class name to None


class StorageBackend(ABC):
    @abstractmethod
    def put(self, key, value): ...

    @abstractmethod
    def get(self, key): ...


@register("memory")
class MemoryBackend(StorageBackend):
    def __init__(self): self._d = {}
    def put(self, k, v): self._d[k] = v
    def get(self, k): return self._d.get(k)


@register("redis")
class RedisBackend(StorageBackend):
    def __init__(self): self._d = {}
    def put(self, k, v): self._d[f"redis:{k}"] = v
    def get(self, k): return self._d.get(f"redis:{k}")


def get_backend(name: str) -> StorageBackend:
    try:
        return _PLUGINS[name]()
    except KeyError:
        raise ValueError(f"unknown backend {name!r}; available: {sorted(_PLUGINS)}") from None


print(f"  registered: {sorted(_PLUGINS)}")
backend = get_backend("redis")                     # driven by config
backend.put("order:1", {"total": 250})
print(f"  get_backend('redis').get('order:1') -> {backend.get('order:1')}")

try:
    get_backend("couchbase")
except ValueError as e:
    print(f"  unknown backend -> {e}")

print("""
  THE CATCH: the decorator only runs when the module is IMPORTED. If
  couchbase_backend.py is never imported, it is never registered — and you get
  'unknown backend' in production with the file sitting right there.
  Fixes: import them in the package __init__.py, or auto-discover with pkgutil.""")


# ================================================================== 2. subclass hook
section("2. __init_subclass__ — registration happens at class DEFINITION")


class Serializer:
    registry: dict[str, type] = {}

    def __init_subclass__(cls, key=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if key:
            Serializer.registry[key] = cls      # no decorator needed

    @abstractmethod
    def dumps(self, obj): ...


class JsonSerializer(Serializer, key="json"):    # note the CLASS KEYWORD ARGUMENT
    def dumps(self, obj):
        import json
        return json.dumps(obj)


class CsvSerializer(Serializer, key="csv"):
    def dumps(self, obj):
        return ",".join(f"{k}={v}" for k, v in obj.items())


print(f"  registry: { {k: v.__name__ for k, v in Serializer.registry.items()} }")
print(f"  json -> {Serializer.registry['json']().dumps({'a': 1, 'b': 2})}")
print(f"  csv  -> {Serializer.registry['csv']().dumps({'a': 1, 'b': 2})}")
print("""
  Cleaner than a metaclass for this job: no MRO conflicts, no magic, and the
  configuration rides on the class statement. Tim Peters' rule applies — if you
  are wondering whether you need a metaclass, you don't.""")


# ================================================================== 3. entry points
section("3. setuptools entry points — a SEPARATE pip package extends you")

print("""  In the PLUGIN package's pyproject.toml:

      [project.entry-points."myapp.storage_backends"]
      s3 = "myapp_s3_plugin:S3Backend"

  In YOUR application:

      from importlib.metadata import entry_points

      def load_plugins():
          for ep in entry_points(group="myapp.storage_backends"):
              _PLUGINS[ep.name] = ep.load()

  Now `pip install myapp-s3-plugin` extends your app with NO change to your repo.
  This is how pytest plugins, Airflow providers and Flask extensions work.""")

# Simulate what entry-point discovery does
SIMULATED_ENTRY_POINTS = {"s3": lambda: type("S3Backend", (StorageBackend,), {
    "put": lambda self, k, v: None, "get": lambda self, k: f"s3-object:{k}"})()}


def load_plugins():
    for name, factory in SIMULATED_ENTRY_POINTS.items():
        _PLUGINS[name] = type(factory())
        print(f"  discovered external plugin: {name!r} -> {_PLUGINS[name].__name__}")


load_plugins()
print(f"  registry is now: {sorted(_PLUGINS)}")
print(f"  get_backend('s3').get('k') -> {get_backend('s3').get('k')}")


# ================================================================== validation
section("4. validate plugins at STARTUP, not on first use")


def validate_startup(configured: list[str]):
    """Fail the deploy, not the 3am request."""
    missing = [n for n in configured if n not in _PLUGINS]
    if missing:
        raise RuntimeError(
            f"configured backends not available: {missing}; have {sorted(_PLUGINS)}")
    for name in configured:
        cls = _PLUGINS[name]
        if not issubclass(cls, StorageBackend):
            raise TypeError(f"{name!r} -> {cls.__name__} does not implement StorageBackend")
    return True


print("  validate(['redis', 's3'])   ->", validate_startup(["redis", "s3"]))
try:
    validate_startup(["redis", "cassandra"])
except RuntimeError as e:
    print(f"  validate(['cassandra'])     -> {e}")
print("""
  A misconfiguration should fail the DEPLOY, loudly, in staging — not surface as a
  KeyError on one unlucky request at 3am. Also expose the active plugin in /health
  and in your startup logs so you can see what is actually loaded.""")


# ================================================================== comparison
section("5. choosing")

rows = [
    ("decorator registry", "internal strategies you control",
     "module must be imported first"),
    ("__init_subclass__", "a family of subclasses in your codebase",
     "only works for SUBCLASSES"),
    ("entry points", "third parties extend you without a PR",
     "packaging overhead; slower discovery"),
    ("class decorator", "opt-in per class, composable",
     "same import problem as a registry"),
    ("plain config + import", "two or three known options",
     "no extensibility — often correct!"),
]
print(f"  {'approach':<22}{'use when':<40}watch out for")
print("  " + "-" * 92)
for approach, when, caveat in rows:
    print(f"  {approach:<22}{when:<40}{caveat}")

print("""
  Define the contract as an ABC or Protocol either way. And do not build a plugin
  system for two implementations you control — an if/else and a config value is
  the right amount of engineering until a third party actually needs to extend you.""")


# EXERCISE 1: forget the `return cls` in the register decorator and see what
#             MemoryBackend becomes. Explain the error you get at first use.
# EXERCISE 2: implement real auto-discovery with pkgutil.iter_modules over a
#             `plugins/` package, so dropping a file in registers it.
# EXERCISE 3: add a `priority` to each plugin and resolve conflicts when two
#             register the same name, instead of raising.
# EXERCISE 4: replace the ABC with a typing.Protocol and confirm an external class
#             that never imports your package still satisfies validate_startup.
