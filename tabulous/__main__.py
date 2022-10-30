from __future__ import annotations

import argparse


class TabulousArgs(argparse.Namespace):
    profile: bool
    debug: bool
    open_file: str | None


class TabulousParser(argparse.ArgumentParser):
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
        self.add_argument("--debug", action="store_true")

    def parse_known_args(
        self, args=None, namespace=None
    ) -> tuple[TabulousArgs, list[str]]:
        args, unknown = super().parse_known_args(args, namespace)
        args = TabulousArgs(**vars(args))
        if not unknown:
            args.open_file = None
        elif len(unknown) == 1:
            args.open_file = unknown[0]
        else:
            raise argparse.ArgumentError("Too many arguments.")
        return args, unknown


def main():
    parser = TabulousParser()

    args, _ = parser.parse_known_args()

    if args.profile:
        from ._utils import CONFIG_PATH

        print(CONFIG_PATH.parent)
        return

    if args.debug:
        import logging

        logger = logging.getLogger("tabulous")
        logging.basicConfig(format="%(levelname)s|| %(message)s")
        logger.setLevel(logging.DEBUG)

    from . import TableViewer

    viewer = TableViewer()

    viewer.show()

    if args.open_file:
        viewer.open(args.open_file)
    return


if __name__ == "__main__":
    main()
