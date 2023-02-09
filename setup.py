from setuptools import setup, find_packages

TABULOUS = "tabulous"

with open(f"{TABULOUS}/__init__.py", encoding="utf-8") as f:
    line = next(iter(f))
    VERSION = line.strip().split()[-1][1:-1]

with open("README.md") as f:
    README = f.read()

setup(
    name=TABULOUS,
    version=VERSION,
    description="A table data viewer for Python",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Hanjin Liu",
    author_email="liuhanjin-sc@g.ecc.u-tokyo.ac.jp",
    license="BSD 3-Clause",
    download_url="https://github.com/hanjinliu/tabulous",
    packages=find_packages(exclude=["docs", "examples", "rst", "tests", "tests.*"]),
    package_data={
        TABULOUS: ["**/*.pyi", "*.pyi", "**/*.svg", "**/*.png", "**/*.qss", "**/*.json"]
    },
    include_package_data=True,
    install_requires=[
        "magicgui>=0.5.1",
        "psygnal>=0.6.1",
        "qtpy>=1.10.0",
        "pandas>=1.5.2",
        "collections-undo>=0.0.7",
        "appdirs>=1.4.4",
        "qtconsole",
        "qt-command-palette>=0.0.5",
        "toml",
        "matplotlib>=3.1",
        "tabulate",
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
    entry_points={
        "console_scripts": [f"{TABULOUS}={TABULOUS}.__main__:main"],
    },
    python_requires=">=3.8",
)
