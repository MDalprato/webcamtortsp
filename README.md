# FaceTime HD to RTSP (macOS)

Script Python per convertire la webcam FaceTime HD in un flusso RTSP usando `ffmpeg`.
Su macOS, per affidabilità, usa `mediamtx` come server RTSP locale.

## Requisiti

- macOS
- Python 3
- ffmpeg
- mediamtx

Installazione con Homebrew:

```bash
brew install ffmpeg
brew install mediamtx
```

## File del progetto

- `facetime_to_rtsp.py`: script principale

## Utilizzo

### 1) Elencare i dispositivi video

```bash
python3 facetime_to_rtsp.py --list-devices
```

Annota l'indice della camera FaceTime HD (es. `0`).

### 2) Avviare lo stream RTSP

```bash
python3 facetime_to_rtsp.py --device-index 0 --port 8554 --path facetime
```

URL RTSP disponibili:

- Locale: `rtsp://127.0.0.1:8554/facetime`
- LAN: `rtsp://<IP_DEL_MAC>:8554/facetime`

Per fermare lo stream: `CTRL+C`.

### 3) Test rapido dello stream

Con `ffplay`:

```bash
ffplay rtsp://127.0.0.1:8554/facetime
```

## Opzioni utili

```bash
python3 facetime_to_rtsp.py --help
```

Parametri principali:

- `--server`: `mediamtx` (default) o `ffmpeg-listen` (fallback)
- `--mediamtx-bin`: path binario mediamtx
- `--device-index`: indice camera avfoundation
- `--resolution`: risoluzione video (default `1280x720`)
- `--fps`: frame rate (default `30`)
- `--preset`: preset x264 (default `veryfast`)
- `--transport`: `tcp` o `udp` (default `tcp`)
- `--port`: porta RTSP (default `8554`)
- `--path`: path stream RTSP (default `facetime`)

## Troubleshooting

- `ffmpeg non trovato`: installa `ffmpeg` e verifica che sia nel `PATH`.
- `mediamtx non trovato`: installa con `brew install mediamtx`.
- Camera non visibile: controlla i permessi macOS per Terminale/Python in:
  `Impostazioni di Sistema > Privacy e Sicurezza > Fotocamera`.
- Stream non raggiungibile da LAN: verifica firewall e che client/server siano sulla stessa rete.
- `Connection refused` in modalità RTSP diretta ffmpeg: usa `--server mediamtx` (default).
- Porta occupata: cambia porta con `--port 8555` (o libera la `8554`).
- `Server returned 400 Bad Request`: ora lo script avvia `mediamtx` con `paths: all: {}`
  per accettare la pubblicazione su qualsiasi path.

## Fallback (non consigliato su macOS)

Se vuoi provare la modalità listen di ffmpeg:

```bash
python3 facetime_to_rtsp.py --server ffmpeg-listen --device-index 0 --port 8554 --path facetime
```
