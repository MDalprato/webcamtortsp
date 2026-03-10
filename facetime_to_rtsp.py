#!/usr/bin/env python3
"""
Converte la webcam FaceTime HD su macOS in un flusso RTSP usando ffmpeg.

Prerequisiti:
  - macOS
  - ffmpeg installato (es. `brew install ffmpeg`)

Esempio:
  python3 facetime_to_rtsp.py --port 8554 --path cam
  Stream disponibile su: rtsp://127.0.0.1:8554/cam
"""

from __future__ import annotations

import argparse
import shlex
import signal
import subprocess
import sys
from typing import Optional


def check_ffmpeg(ffmpeg_bin: str) -> None:
    try:
        subprocess.run(
            [ffmpeg_bin, "-version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SystemExit(
            f"ffmpeg non trovato ({ffmpeg_bin}). Installa ffmpeg, ad esempio: brew install ffmpeg"
        ) from exc


def list_avfoundation_devices(ffmpeg_bin: str) -> None:
    # ffmpeg stampa l'elenco device su stderr con avfoundation.
    cmd = [ffmpeg_bin, "-f", "avfoundation", "-list_devices", "true", "-i", ""]
    print("Cerco dispositivi video disponibili...\n")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = (proc.stderr or "") + (proc.stdout or "")
    print(output.strip())


def build_ffmpeg_cmd(args: argparse.Namespace) -> list[str]:
    input_selector = f"{args.device_index}:none"
    url = f"rtsp://0.0.0.0:{args.port}/{args.path.lstrip('/')}"

    return [
        args.ffmpeg_bin,
        "-f",
        "avfoundation",
        "-framerate",
        str(args.fps),
        "-video_size",
        args.resolution,
        "-i",
        input_selector,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        args.preset,
        "-tune",
        "zerolatency",
        "-pix_fmt",
        "yuv420p",
        "-f",
        "rtsp",
        "-rtsp_transport",
        args.transport,
        "-rtsp_flags",
        "listen",
        url,
    ]


def run_stream(args: argparse.Namespace) -> int:
    check_ffmpeg(args.ffmpeg_bin)

    if args.list_devices:
        list_avfoundation_devices(args.ffmpeg_bin)
        return 0

    cmd = build_ffmpeg_cmd(args)
    printable = " ".join(shlex.quote(p) for p in cmd)

    print("Avvio stream RTSP...")
    print(f"Comando:\n{printable}\n")
    print(f"URL locale: rtsp://127.0.0.1:{args.port}/{args.path.lstrip('/')}")
    print("Premi CTRL+C per fermare.\n")

    proc: Optional[subprocess.Popen[str]] = None
    try:
        proc = subprocess.Popen(cmd)
        return proc.wait()
    except KeyboardInterrupt:
        print("\nInterruzione richiesta, chiusura in corso...")
        if proc and proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try:
                return proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.terminate()
                return proc.wait(timeout=5)
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pubblica la webcam FaceTime HD come stream RTSP (macOS)."
    )
    parser.add_argument(
        "--ffmpeg-bin",
        default="ffmpeg",
        help="Percorso o nome binario ffmpeg (default: ffmpeg)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Mostra i device avfoundation e termina.",
    )
    parser.add_argument(
        "--device-index",
        type=int,
        default=0,
        help="Indice camera avfoundation (default: 0)",
    )
    parser.add_argument(
        "--resolution",
        default="1280x720",
        help="Risoluzione video, es. 1280x720 (default: 1280x720)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Frame rate (default: 30)",
    )
    parser.add_argument(
        "--preset",
        default="veryfast",
        help="Preset x264 (default: veryfast)",
    )
    parser.add_argument(
        "--transport",
        choices=["tcp", "udp"],
        default="tcp",
        help="Trasporto RTSP (default: tcp)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8554,
        help="Porta RTSP locale (default: 8554)",
    )
    parser.add_argument(
        "--path",
        default="facetime",
        help="Path stream RTSP (default: facetime)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_stream(args)


if __name__ == "__main__":
    sys.exit(main())
