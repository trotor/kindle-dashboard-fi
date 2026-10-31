import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from saasahko.app import log, make_server, start_refresher
from saasahko.config import load_config
from saasahko.render import render
from saasahko.state import build_state
from saasahko.store import DataStore


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="saasahko")
    sub = parser.add_subparsers(dest="cmd", required=True)
    serve = sub.add_parser("serve", help="run the HTTP server")
    serve.add_argument("--config", type=Path, required=True)
    preview = sub.add_parser("preview", help="refresh once and render to a PNG file")
    preview.add_argument("out", type=Path)
    preview.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(message)s")
    cfg = load_config(args.config)
    store = DataStore(cfg)
    if args.cmd == "serve":
        start_refresher(store)
        server = make_server(cfg, store)
        log.info("serving on port %d", server.server_address[1])
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    else:
        store.refresh()
        snap = store.snapshot()
        if snap.last_error:
            log.warning("fetch problem: %s", snap.last_error)
        state = build_state(snap, cfg, datetime.now(timezone.utc), None)
        render(state).save(args.out, "PNG")
        log.info("wrote %s", args.out)


if __name__ == "__main__":
    main()
