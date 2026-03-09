from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from visionscore.plugins.info import PluginInfo

if TYPE_CHECKING:
    from visionscore.analyzers.base import BaseAnalyzer

logger = logging.getLogger(__name__)


def _base_analyzer_cls() -> type:
    """Lazy import to avoid circular dependency at module level."""
    from visionscore.analyzers.base import BaseAnalyzer

    return BaseAnalyzer


class PluginRegistry:
    """Discover, register, and manage analyzer plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, tuple[PluginInfo, type[BaseAnalyzer]]] = {}

    def register(self, analyzer_cls: type[BaseAnalyzer], info: PluginInfo) -> None:
        """Register an analyzer plugin."""
        self._plugins[info.name] = (info, analyzer_cls)

    def unregister(self, name: str) -> None:
        """Remove a registered plugin by name."""
        self._plugins.pop(name, None)

    def get_all(self) -> list[tuple[PluginInfo, type[BaseAnalyzer]]]:
        """Return all registered plugins as (info, class) pairs."""
        return list(self._plugins.values())

    def get(self, name: str) -> tuple[PluginInfo, type[BaseAnalyzer]] | None:
        """Look up a plugin by name."""
        return self._plugins.get(name)

    def discover_entry_points(self) -> None:
        """Discover plugins from the ``visionscore.analyzers`` entry-point group."""
        try:
            from importlib.metadata import entry_points

            eps = entry_points(group="visionscore.analyzers")
        except Exception:
            return

        for ep in eps:
            try:
                cls = ep.load()
                info = getattr(cls, "plugin_info", None)
                if info is None or not isinstance(info, PluginInfo):
                    logger.warning(
                        "Entry point '%s' missing plugin_info, skipped", ep.name
                    )
                    continue
                base = _base_analyzer_cls()
                if not (isinstance(cls, type) and issubclass(cls, base)):
                    logger.warning(
                        "Entry point '%s' is not a BaseAnalyzer subclass, skipped",
                        ep.name,
                    )
                    continue
                self.register(cls, info)
            except Exception as exc:
                logger.warning("Failed to load entry point '%s': %s", ep.name, exc)

    def discover_directory(self, path: Path) -> None:
        """Discover plugins from ``.py`` files in *path*."""
        if not path.is_dir():
            return

        for py_file in sorted(path.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"visionscore_plugin_{py_file.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                base = _base_analyzer_cls()
                for _name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        obj is not base
                        and issubclass(obj, base)
                        and hasattr(obj, "plugin_info")
                        and isinstance(obj.plugin_info, PluginInfo)
                    ):
                        self.register(obj, obj.plugin_info)
            except Exception as exc:
                logger.warning("Failed to load plugin '%s': %s", py_file.name, exc)


_default_registry: PluginRegistry | None = None


def get_default_registry() -> PluginRegistry:
    """Return the shared plugin registry singleton."""
    global _default_registry
    if _default_registry is None:
        _default_registry = PluginRegistry()
    return _default_registry
