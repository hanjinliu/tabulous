set shell := ["powershell.exe", "-c"]

doc:
	sphinx-apidoc -f -o ./rst/apidoc ./tabulous
	sphinx-build -b html ./rst ./docs

images:
	python ./image/generate_figs.py

images-rst:
	python ./rst/fig/generate_figs.py

watch-rst:
	watchfiles "sphinx-build -b html ./rst ./_docs_temp" rst

installer:
	pyinstaller .\launch.py --onefile --noconsole --windowed --name tabulous  \
	--icon .\tabulous\_qt\_icons\tabulous.ico  \
	--add-data ".\tabulous\_qt\_icons;.\tabulous\_qt\_icons"  \
	--add-data ".\tabulous\style\_style.qss;.\tabulous\style"  \
	--add-data ".\tabulous\style\defaults.json;.\tabulous\style"

test:
    hatch -v run test:run
