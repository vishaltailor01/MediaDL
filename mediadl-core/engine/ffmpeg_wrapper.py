import subprocess
import os

class FfmpegEngine:
    def __init__(self, ffmpeg_path="ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def convert(self, input_path: str, output_path: str, format: str):
        """
        Runs a deterministic conversion process using ffmpeg.
        """
        command = [
            self.ffmpeg_path,
            "-y", # overwrite output
            "-i", input_path,
        ]
        
        if format == "mp3":
            command.extend(["-vn", "-acodec", "libmp3lame", "-q:a", "2"])
        elif format == "mp4":
            command.extend(["-vcodec", "libx264", "-acodec", "aac"])
            
        command.append(output_path)
        return self._run(command, output_path)

    def trim(self, input_path: str, output_path: str, start: str, duration: str):
        """
        Trims media deterministically.
        """
        command = [
            self.ffmpeg_path,
            "-y"
        ]
        if start:
            command.extend(["-ss", start])
        
        command.extend(["-i", input_path])
        
        if duration:
            command.extend(["-t", duration])
            
        command.extend(["-c", "copy", output_path])
        return self._run(command, output_path)

    def _run(self, command: list, output_path: str):
        # Run conversion sandboxed
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg Error:\n{stderr}")
            
        return output_path
