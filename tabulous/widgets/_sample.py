from __future__ import annotations
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

_SAMPLE_PROVIDERS: dict[str, Callable[[str], pd.DataFrame]] = {}


def register_sample_plugin(
    provider: Callable[[str], pd.DataFrame] | None = None,
    plugin_name: str | None = None,
):
    def _register(func):
        nonlocal plugin_name
        if plugin_name is None:
            plugin_name = func.__name__
        _SAMPLE_PROVIDERS[plugin_name] = func
        return func

    if provider is None:
        return _register
    else:
        return _register(provider)


@register_sample_plugin
def seaborn(name: str):
    import seaborn as sns

    return sns.load_dataset(name)


def open_sample(name: str, plugin_name: str) -> pd.DataFrame:
    provider = _SAMPLE_PROVIDERS.get(plugin_name)
    if provider is None:
        raise ValueError(f"No plugin named {plugin_name}")
    return provider(name)
