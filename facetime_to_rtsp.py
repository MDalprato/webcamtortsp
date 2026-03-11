#!/usr/bin/env python3
"""
Converte la webcam FaceTime HD su macOS in un flusso RTSP usando ffmpeg.

Prerequisiti:
  - macOS
  - ffmpeg installato (es. `brew install ffmpeg`)
  - mediamtx installato (consigliato su macOS):
      `brew install mediamtx`

Esempio:
  python3 facetime_to_rtsp.py --port 8554 --path cam
  Stream disponibile su: rtsp://127.0.0.1:8554/cam
"""

from __future__ import annotations

import argparse
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from typing import Optional


def check_binary(binary: str, install_hint: str) -> None:
    try:
        subprocess.run(
            [binary, "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Comando non trovato ({binary}). {install_hint}") from exc


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


def build_rtsp_url(args: argparse.Namespace) -> str:
    path = args.path.lstrip("/")
    if args.server == "mediamtx":
        return f"rtsp://127.0.0.1:{args.port}/{path}"
    return f"rtsp://127.0.0.1:{args.port}/{path}?listen=1"


def build_ffmpeg_cmd(args: argparse.Namespace) -> list[str]:
    input_selector = f"{args.device_index}:none"
    url = build_rtsp_url(args)

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
        url,
    ]


def start_mediamtx(args: argparse.Namespace) -> tuple[subprocess.Popen[str], str]:
    check_binary(
        args.mediamtx_bin,
        "Installa mediamtx, ad esempio: brew install mediamtx",
    )
    with tempfile.NamedTemporaryFile(
        mode="w", prefix="mediamtx-", suffix=".yml", delete=False
    ) as tmp:
        tmp.write(
            "\n".join(
                [
                    "logLevel: info",
                    f"rtspAddress: :{args.port}",
                    "paths:",
                    "  all: {}",
                    "",
                ]
            )
        )
        config_path = tmp.name

    cmd = [args.mediamtx_bin, config_path]
    print("Avvio server RTSP locale (mediamtx)...")
    print(f"Comando server:\n{' '.join(shlex.quote(p) for p in cmd)}\n")
    proc = subprocess.Popen(cmd)
    time.sleep(0.8)
    if proc.poll() is not None:
        raise SystemExit(
            f"mediamtx si è chiuso subito. Verifica che la porta {args.port} non sia già in uso."
        )
    return proc, config_path


def stop_process(proc: Optional[subprocess.Popen[str]]) -> None:
    if not proc or proc.poll() is not None:
        return
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.terminate()
        proc.wait(timeout=5)


def run_stream(args: argparse.Namespace) -> int:
    check_ffmpeg(args.ffmpeg_bin)

    if args.list_devices:
        list_avfoundation_devices(args.ffmpeg_bin)
        return 0

    server_proc: Optional[subprocess.Popen[str]] = None
    mediamtx_config: Optional[str] = None
    if args.server == "mediamtx":
        server_proc, mediamtx_config = start_mediamtx(args)

    cmd = build_ffmpeg_cmd(args)
    printable = " ".join(shlex.quote(p) for p in cmd)
    public_url = f"rtsp://127.0.0.1:{args.port}/{args.path.lstrip('/')}"

    print("Avvio stream RTSP...")
    print(f"Comando:\n{printable}\n")
    print(f"URL locale: {public_url}")
    print("Premi CTRL+C per fermare.\n")

    proc: Optional[subprocess.Popen[str]] = None
    try:
        proc = subprocess.Popen(cmd)
        code = proc.wait()
        if code != 0 and args.server == "ffmpeg-listen":
            print(
                "\nSuggerimento: usa --server mediamtx (default) per evitare i limiti "
                "della modalità listen di ffmpeg su macOS."
            )
        return code
    except KeyboardInterrupt:
        print("\nInterruzione richiesta, chiusura in corso...")
        stop_process(proc)
        return 0
    finally:
        stop_process(server_proc)
        if mediamtx_config:
            try:
                os.remove(mediamtx_config)
            except OSError:
                pass


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
        "--server",
        choices=["mediamtx", "ffmpeg-listen"],
        default="mediamtx",
        help="Backend server RTSP (default: mediamtx)",
    )
    parser.add_argument(
        "--mediamtx-bin",
        default="mediamtx",
        help="Percorso o nome binario mediamtx (default: mediamtx)",
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
