import argparse
from . import __version__


def main():
    parser = argparse.ArgumentParser(description="Command line interface of tabulous.")
    parser.add_argument(
        "-v", "--version", action="version", version=f"tabulous version {__version__}"
    )

    args, unknown = parser.parse_known_args()

    from . import TableViewer

    viewer = TableViewer()
    if not unknown:
        pass
    elif len(unknown) == 1:
        viewer.open(unknown[0])
    else:
        raise RuntimeError

    from ._qt._app import run_app

    run_app()


if __name__ == "__main__":
    main()
