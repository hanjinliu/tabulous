from __future__ import annotations

import argparse
from pathlib import Path


class TabulousArgs(argparse.Namespace):
    """Tabulous specific arguments"""

    profile: bool
    user_dir: bool
    debug: bool
    init_config: bool
    init_history: bool
    open_file: str | None


class TabulousParser(argparse.ArgumentParser):
    """Tabulous specific argument parser"""

    def __init__(self):
        from . import __version__

        super().__init__(description="Command line interface of tabulous.")
        self.add_argument(
            "-v",
            "--version",
            action="version",
            version=f"tabulous version {__version__}",
        )
        self.add_argument("--profile", action="store_true")
        self.add_argument("--user-dir", action="store_true")
        self.add_argument("--debug", action="store_true")
        self.add_argument("--init-config", action="store_true")
        self.add_argument("--init-history", action="store_true")

    def parse_known_args(
        self, args=None, namespace=None
    ) -> tuple[TabulousArgs, list[str]]:
        args, unknown = super().parse_known_args(args, namespace)
        args = TabulousArgs(**vars(args))
        if not unknown:
            args.open_file = None
        elif len(unknown) == 1:
            path = unknown[0]
            if Path(path).suffix:
                args.open_file = path
            else:
                args.open_file = None
        else:
            raise argparse.ArgumentError("Too many arguments.")
        return args, unknown


def main():
    parser = TabulousParser()

    args, _ = parser.parse_known_args()

    if args.profile or args.user_dir:
        from ._utils import CONFIG_PATH

        return print(CONFIG_PATH.parent)

    if args.debug:
        import logging

        logger = logging.getLogger("tabulous")
        logging.basicConfig(format="%(levelname)s|| %(message)s")
        logger.setLevel(logging.DEBUG)

    if args.init_config:
        from ._utils import CONFIG_PATH, TabulousConfig

        CONFIG_PATH.unlink(missing_ok=True)
        TabulousConfig.from_toml(CONFIG_PATH).as_toml()
        return print(f"tabulous config file initialized at {str(CONFIG_PATH)}.")

    if args.init_history:
        from ._utils import TXT_PATH

        TXT_PATH.write_text("")

    from . import TableViewer
    from ._async_importer import import_plt, import_scipy
    from ._qt._console import import_qtconsole_threading

    viewer = TableViewer()

    if args.open_file:
        viewer.open(args.open_file)

    import_qtconsole_threading()
    import_plt()
    import_scipy()
    viewer.show()
    return


if __name__ == "__main__":
    main()
