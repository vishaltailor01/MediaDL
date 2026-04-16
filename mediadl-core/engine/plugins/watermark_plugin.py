import subprocess
from engine.plugin_manager import MediaPlugin

class WatermarkPlugin(MediaPlugin):
    @property
    def name(self) -> str:
        return "watermark"

    def execute(self, input_path: str, output_path: str, **kwargs) -> str:
        text = kwargs.get("text", "MediaDL Core")
        # Ensure exact paths and string escaping
        drawtext_filter = f"drawtext=text='{text}':fontcolor=white:fontsize=24:x=10:y=10"
        
        command = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", drawtext_filter,
            "-c:a", "copy",
            output_path
        ]
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Plugin (watermark) failed:\n{stderr}")
            
        return output_path
