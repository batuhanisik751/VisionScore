from __future__ import annotations

from visionscore.plugins.info import PluginInfo
from visionscore.plugins.registry import PluginRegistry, get_default_registry

__all__ = ["PluginInfo", "PluginRegistry", "get_default_registry", "register_bundled_plugins"]


def register_bundled_plugins(registry: PluginRegistry) -> None:
    """Register the example plugins that ship with VisionScore."""
    from visionscore.plugins.instagram import InstagramReadinessAnalyzer

    info = InstagramReadinessAnalyzer.plugin_info
    if info is not None:
        registry.register(InstagramReadinessAnalyzer, info)
