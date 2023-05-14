import sys

sys.stderr.write(
    """
    ===============================================================
    tabulous does not support `python setup.py install`. Please use

        $ python -m pip install .

    instead.
    ===============================================================
    """
)
sys.exit(1)

setup(
    name="tabulous",
    description="A table data viewer for Python",
    long_description_content_type="text/markdown",
    author="Hanjin Liu",
    author_email="liuhanjin-sc@g.ecc.u-tokyo.ac.jp",
    license="BSD 3-Clause",
    download_url="https://github.com/hanjinliu/tabulous",
    include_package_data=True,
    install_requires=[
        "magicgui>=0.5.1",
        "psygnal>=0.9.0",
        "qtpy>=1.10.0",
        "pandas>=1.5.2",
        "collections-undo>=0.0.7",
        "appdirs>=1.4.4",
        "qtconsole",
        "qt-command-palette>=0.0.6",
        "toml",
        "matplotlib>=3.1",
        "tabulate",
        "requests",
    ],
    extras_require={
        "all": [
            "seaborn>=0.11",
            "pyqt5>=5.12.3",
            "scipy>=1.7",
            "scikit-learn>=1.1",
        ],
        "pyqt5": ["pyqt5>=5.12.3"],
        "pyqt6": ["pyqt6>=6.3.1"],
        "scikit-learn": ["scikit-learn>=1.0"],
    },
    python_requires=">=3.8",
)
