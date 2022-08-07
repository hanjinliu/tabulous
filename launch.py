from tabulous import TableViewer
import sys

if __name__ == "__main__":
    viewer = TableViewer()
    if len(sys.argv) > 1:
        viewer.open_sample(sys.argv[1])
    viewer._qwidget.resize(800, 600)
    viewer.show()
