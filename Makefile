doc:
	sphinx-apidoc -f -o ./rst/apidoc ./tabulous
	sphinx-build -b html ./rst ./docs

release:
	python setup.py sdist
	python setup.py bdist_wheel
	twine upload --repository testpypi dist/*
	twine upload --repository pypi dist/*

images:
	python ./image/generate_figs.py

watch-rst:
	watchfiles "sphinx-build -b html ./rst ./_docs_temp" rst
