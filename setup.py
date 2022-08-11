from setuptools import setup, find_packages

with open("tabulous/__init__.py", encoding="utf-8") as f:
    line = next(iter(f))
    VERSION = line.strip().split()[-1][1:-1]

with open("README.md") as f:
    readme = f.read()

setup(
    name="tabulous",
    version=VERSION,
    description="A table data viewer for Python",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Hanjin Liu",
    author_email="liuhanjin-sc@g.ecc.u-tokyo.ac.jp",
    license="BSD 3-Clause",
    download_url="https://github.com/hanjinliu/tabulous",
    packages=find_packages(exclude=["docs", "examples", "rst", "tests", "tests.*"]),
    package_data={"tabulous": ["**/*.pyi", "*.pyi", "**/*.svg"]},
    include_package_data=True,
    install_requires=[
        "magicgui>=0.5.1",
        "qtpy>=1.10.0",
        "pandas>=1.0.0",
        "collections-undo>=0.0.4",
        "qtconsole",
    ],
    extras_require={"all": ["seaborn>=0.11", "matplotlib>=3.1", "pyqt5>=5.12.3"]},
    entry_points={
        "console_scripts": [
            "tabulous=tabulous.__main__:main",
        ],
    },
    python_requires=">=3.8",
)
