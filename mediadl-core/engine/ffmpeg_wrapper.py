import subprocess
import os

class FfmpegEngine:
    def __init__(self, ffmpeg_path="ffmpeg"):
        if os.path.isdir(ffmpeg_path):
            for name in ["ffmpeg.exe", "ffmpeg"]:
                candidate = os.path.join(ffmpeg_path, name)
                if os.path.exists(candidate):
                    self.ffmpeg_path = candidate
                    break
            else:
                self.ffmpeg_path = os.path.join(ffmpeg_path, "ffmpeg")
        else:
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

    async def compile_course_video(self, segments_data: list, output_video_path: str) -> str:
        """
        Asynchronously compiles slide images and narrative audio wavs into a final MP4 course video.
        segments_data is a list of dicts: [{"slide_path": str, "audio_path": str}]
        """
        import asyncio
        
        # 1. Create individual sub-clips
        sub_clips = []
        for i, seg in enumerate(segments_data):
            slide_img = seg["slide_path"]
            audio_wav = seg["audio_path"]
            
            temp_dir = os.path.dirname(output_video_path)
            sub_clip_path = os.path.join(temp_dir, f"segment_{i}_{os.path.basename(audio_wav)}.mp4")
            
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-loop", "1",
                "-i", slide_img,
                "-i", audio_wav,
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                sub_clip_path
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"FFmpeg Segment {i} Error:\n{stderr.decode('utf-8', errors='replace')}")
                
            sub_clips.append(sub_clip_path)
            
        # 2. Concat all sub-clips using filtercomplex concat
        concat_cmd = [self.ffmpeg_path, "-y"]
        for clip in sub_clips:
            concat_cmd.extend(["-i", clip])
            
        n = len(sub_clips)
        filter_inputs = "".join(f"[{i}:v][{i}:a]" for i in range(n))
        filter_str = f"{filter_inputs}concat=n={n}:v=1:a=1[outv][outa]"
        
        concat_cmd.extend([
            "-filter_complex", filter_str,
            "-map", "[outv]",
            "-map", "[outa]",
            output_video_path
        ])
        
        proc = await asyncio.create_subprocess_exec(
            *concat_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg Concat Error:\n{stderr.decode('utf-8', errors='replace')}")
            
        # Clean up intermediate segment MP4s
        for clip in sub_clips:
            try:
                os.remove(clip)
            except OSError:
                pass
                
        return output_video_path

