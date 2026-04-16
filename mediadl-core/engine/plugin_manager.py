import importlib
import os
import sys

class MediaPlugin:
    """Base class for all MediaDL plugins."""
    @property
    def name(self) -> str:
        raise NotImplementedError

    def execute(self, input_path: str, output_path: str, **kwargs) -> str:
        """Executes the plugin operation."""
        raise NotImplementedError

class PluginManager:
    def __init__(self, plugin_dir: str = None):
        if plugin_dir is None:
            plugin_dir = os.path.join(os.path.dirname(__file__), "plugins")
        self.plugin_dir = plugin_dir
        self.plugins = {}
        self._load_plugins()

    def _load_plugins(self):
        if not os.path.exists(self.plugin_dir):
            return
            
        sys.path.insert(0, self.plugin_dir)
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(module_name)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, MediaPlugin) and attr is not MediaPlugin:
                            plugin_instance = attr()
                            self.plugins[plugin_instance.name] = plugin_instance
                            print(f"[Plugins] Loaded plugin: {plugin_instance.name}")
                except Exception as e:
                    print(f"[Plugins] Failed to load plugin {filename}: {e}")
        sys.path.pop(0)

    def run_plugin(self, name: str, input_path: str, output_path: str, **kwargs) -> str:
        if name not in self.plugins:
            raise ValueError(f"Plugin '{name}' not found. Available: {list(self.plugins.keys())}")
        return self.plugins[name].execute(input_path, output_path, **kwargs)
