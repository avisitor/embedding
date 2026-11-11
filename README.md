# Hawaiian Corpus Embedding Service

FastAPI app (`embed.py`) served by gunicorn. Provides sentence embeddings for
the Noiʻiʻōlelo corpus and its search providers (`EMBEDDING_SERVICE_URL`,
normally `http://localhost:5000`).

## Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /embed` | `{"text", "prefix"="passage: ", "model"}` → one vector |
| `POST /embed_sentences` | `{"sentences": [...], "prefix", "model"}` → list of vectors |
| `POST /analyze` | spaCy named entities for `{"sentence"}` |
| `GET /health`, `GET /memory` | Liveness and process memory |

Models: `intfloat/multilingual-e5-small` (384-dim, default) and
`intfloat/multilingual-e5-large-instruct` (1024-dim), plus spaCy
`en_core_web_sm`. All of them are loaded when the process starts.

## On-demand operation

With the models loaded, the process uses about 1.6–3.4 GB (peaks above 5 GB), and
calls are infrequent. Instead of running all the time, the service is
socket-activated and exits when idle:

```
client ─► :5000  hawaiian-embedding.socket        (always listening, ~no memory)
             └─► hawaiian-embedding-proxy.service  systemd-socket-proxyd --exit-idle-time
                    └─► 127.0.0.1:5001  hawaiian-embedding.service  (gunicorn + models)
```

- The first connection starts the backend. The proxy waits until `/health`
  responds (`ExecStartPost`), so that first request is held for about 11 s
  and then served normally. Later requests take about 0.1 s.
- After the idle timeout with no traffic, the proxy exits. The backend has
  `StopWhenUnneeded=yes`, so it stops too and frees all of its memory. The
  socket stays open and starts everything again on the next request.
- The idle timer starts when the last connection closes, so a long ingestion
  run keeps the service up until the timeout has passed after it finishes.
- Unloading the models inside the running process frees little memory (in a
  test, the process still held 2.4 GB), which is why the whole process exits.

### Changing the idle timeout

The timeout is `EMBEDDING_IDLE_TIMEOUT` in `idle.env`, written as a systemd time span
(`30min`, `1h`, `2h30min`, `1d`). The default is `1h`.

```bash
./service_control.sh idle          # show the current value
./service_control.sh idle 2h       # set the value and apply it
```

If you edit the file by hand, run `sudo systemctl restart hawaiian-embedding-proxy.service`
and then send one request (`curl localhost:5000/health`). The proxy starts its idle timer only
after a connection closes, so after a restart with no traffic the service never stops. `idle.env` is a required file: if it is missing, the proxy fails to start
rather than using a default.

To keep the models loaded permanently, set a very long span (e.g. `365d`).

## Control

```bash
./service_control.sh status|start|stop|restart|logs|health|warm|enable|disable
```

- `start` and `enable` act on the socket. `restart` reloads the backend (use it
  after editing `embed.py`).
- `warm` is an alias for `health`, not a separate preload path: both call
  `GET /health`, which starts the socket-activated backend and loads the
  models. Use either one before an interactive demo so nobody waits on a cold
  start.

## Installation files

| File | Installed to |
|---|---|
| `systemd/hawaiian-embedding.socket` | `/etc/systemd/system/` (enabled) |
| `systemd/hawaiian-embedding-proxy.service` | `/etc/systemd/system/` |
| `systemd/hawaiian-embedding.service` | `/etc/systemd/system/` (not enabled; started only by the socket and proxy) |
| `systemd/hawaiian_embedding_proxy.te` | SELinux module |

```bash
./service_control.sh install
sudo systemctl enable --now hawaiian-embedding.socket
```

### SELinux

SELinux is enforcing and confines `systemd-socket-proxyd` to the
`systemd_socket_proxyd_t` domain. That domain is not allowed to bind port 5000
(`commplex_main_port_t`) or connect to port 5001 (`commplex_link_port_t`).
Without the local module, the socket fails with `Failed to create listening
socket (0.0.0.0:5000): Permission denied`. Build and load the module with:

```bash
cd /tmp
checkmodule -M -m -o hawaiian_embedding_proxy.mod /var/www/html/embedding_service/systemd/hawaiian_embedding_proxy.te
semodule_package -o hawaiian_embedding_proxy.pp -m hawaiian_embedding_proxy.mod
sudo semodule -i hawaiian_embedding_proxy.pp
```

The module file name must match the module name (`hawaiian_embedding_proxy`).
If you change either port, update the `.te` file and reload the module.
