"""Load a city configuration file and resolve paths."""
from pathlib import Path
import yaml


class Config(dict):
    """Dictionary with attribute access and path helpers."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def data(self, relative: str) -> Path:
        return Path(self["data_dir"]) / relative

    def out(self, relative: str) -> Path:
        p = Path(self["output_dir"]) / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def has(self, section: str) -> bool:
        s = self.get(section)
        if not s:
            return False
        if isinstance(s, dict) and s.get("enabled") is False:
            return False
        f = s.get("file") if isinstance(s, dict) else None
        return f is None or self.data(f).exists()


def load(path: str) -> Config:
    with open(path) as fh:
        cfg = Config(yaml.safe_load(fh))
    for key in ("requests", "centerlines", "chronic", "matching", "breakeven"):
        if key not in cfg:
            raise ValueError(f"config is missing the '{key}' section")
    return cfg
