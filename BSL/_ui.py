import os as _os
import json as _json
import pathlib as _pathlib
import time
import uuid as _uuid

from BSL import _constants

try:
    from PySide2 import QtWidgets as _QtWidgets
    from PySide2 import QtCore as _QtCore
    from PySide2 import QtGui as _QtGui
    from PySide2 import QtWebEngineWidgets as _QtWebEngineWidgets
    from PySide2 import QtWebChannel as _QtWebChannel
    from shiboken2 import wrapInstance as _wrapInstance
    PYSIDE2 = True
    PYSIDE6 = False

except:
    from PySide6 import QtWidgets as _QtWidgets
    from PySide6 import QtCore as _QtCore
    from PySide6 import QtWebEngineWidgets as _QtWebEngineWidgets
    from PySide6 import QtWebEngineCore as _QtWebEngineCore
    from PySide6 import QtWebChannel as _QtWebChannel
    from shiboken6 import wrapInstance as _wrapInstance
    PYSIDE2 = False
    PYSIDE6 = True


def _exec(widget):
    if PYSIDE2:
        return widget.exec_()
    return widget.exec()


class _EditorInterface(_QtCore.QObject):
    modifiedChanged = _QtCore.Signal(bool)

    @_QtCore.Slot(bool)
    def setModified(self, modified):
        # print("Editor reports modified =", modified)
        self.modifiedChanged.emit(modified)


    @_QtCore.Slot(str, result=str)
    def test(self, value):
        print(f"test: '{value}'")
        return value


def _get_uuid():
    return _uuid.uuid4().hex


class _BSLEditorTab:
    def __init__(self, s_id, d_data, parent=None):
        self._parent = None
        self._s_id = s_id

        self._path = None
        self._s_content = ""
        self._s_language = "bsl"
        self._b_modified = True

        if d_data is not None:
            self._path = _pathlib.Path(d_data["path"])
            self._s_language = d_data["language"]
            self._b_modified = False
            self._s_content = self._path.read_text()

        self._web_view = _QtWebEngineWidgets.QWebEngineView(parent=parent)
        self._web_view.setObjectName(self._s_id)

        # Set up a QWebChannel for this web view.
        self._channel = _QtWebChannel.QWebChannel(self._web_view.page())

        self._interface = _EditorInterface()
        self._interface.modifiedChanged.connect(self.cb_modified)

        self._channel.registerObject("pyEditor", self._interface)
        self._web_view.page().setWebChannel(self._channel)

        if PYSIDE6:
            self._web_view.settings().setAttribute(_QtWebEngineCore.QWebEngineSettings.LocalContentCanAccessFileUrls, True)
            self._web_view.settings().setAttribute(_QtWebEngineCore.QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)

        # Load the minimal HTML file (which sets up the Monaco editor).
        html_path = str((_constants.PATH_BASE/"res"/"mini.html").absolute())
        if not _os.path.exists(html_path):
            print("ERROR: html not found at", html_path)

        self._web_view.setUrl(_QtCore.QUrl.fromLocalFile(html_path))

        self._web_view.page().loadFinished.connect(self.cb_loadFinished)

    def id(self):
        return self._s_id

    def path(self) -> _pathlib.Path:
        return self._path

    def name(self):
        if self._path is None:
            return "Untitled"
        return self._path.name

    def title(self):
        return self.name() + (" *" if self._b_modified else "")

    def cb_loadFinished(self, *args, **kwargs):
        d_data = {"title": self.title(), "content": self._s_content, "language": self._s_language}
        self._web_view.page().runJavaScript(f"initializeEditor({_json.dumps(d_data)});")

    def cb_modified(self, b_modified):
        self._b_modified = b_modified

        if self._parent is None:
            return

        for i in range(self._parent.count()):
            if self._parent.widget(i) == self.widget():
                self._parent.setTabText(i, self.title())
                self._parent.setTabToolTip(i, str(self._path))

    def is_modified(self):
        return self._b_modified

    def save_as(self, path=None, s_content=None):
        if path is None:
            path = self._path

        if path is None:
            print("Cant save to 'None'")
            return False

        self._path = _pathlib.Path(path).absolute().resolve()
        if s_content is not None:
            self._s_content = s_content
        self._path.write_text(self._s_content)
        self.cb_modified(False)
        return True

    def widget(self):
        return self._web_view

    def add_to_widget(self, parent):
        self._parent = parent
        parent.addTab(self.widget(), self.title())
        self.cb_modified(self._b_modified)

    def remove_from_widget(self):
        for i in range(self._parent.count()):
            if self._parent.widget(i) == self.widget():
                self._parent.removeTab(i)
                self._parent = None
                self.widget().deleteLater()
                break

    def set_active(self):
        if self._parent is None:
            return

        for i in range(self._parent.count()):
            if self._parent.widget(i) == self.widget():
                self._parent.setCurrentIndex(i)

    def reload(self):
        if self.is_modified():
            return

        s_content = self.path().read_text()
        self._web_view.page().runJavaScript(f"setEditorContent({s_content});")


class _BSLEditor(_QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(_BSLEditor, self).__init__(parent)
        self.setObjectName("BSLEditor")

        self._d_tabs = {}

        self._build()
        self._connect()

        self.cb_reload_graphs()

    def _build(self):
        layout = _QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tb_main = _QtWidgets.QToolBar()
        layout.addWidget(self._tb_main)
        self._action_new = self._tb_main.addAction("New")
        self._action_open = self._tb_main.addAction("Open")
        self._action_save = self._tb_main.addAction("Save")
        self._action_build = self._tb_main.addAction("Build")

        self._cbx_method = _QtWidgets.QComboBox()
        self._cbx_method.addItems(["vnn"])
        # self.cbx_method.addItems(["vnn", "xml", "json"])
        self._tb_main.addWidget(self._cbx_method)

        self._cbx_graph = _QtWidgets.QComboBox()
        self._cbx_graph.setMinimumWidth(200)
        self._btn_graph_reload = _QtWidgets.QToolButton()
        self._btn_graph_reload.setIcon(self._btn_graph_reload.style().standardPixmap(_QtWidgets.QStyle.StandardPixmap.SP_BrowserReload, None))
        self._tb_main.addWidget(self._cbx_graph)
        self._tb_main.addWidget(self._btn_graph_reload)

        # self._spacer = _QtWidgets.QSpacerItem(10, 1)
        self._btn_help = _QtWidgets.QToolButton()
        self._btn_help.setIcon(self._btn_help.style().standardPixmap(_QtWidgets.QStyle.StandardPixmap.SP_MessageBoxQuestion, None))
        self._tb_main.addSeparator()
        self._tb_main.addWidget(self._btn_help)

        # Create the native tab widget.
        self._tabs_editors = _QtWidgets.QTabWidget()
        layout.addWidget(self._tabs_editors)

        self._tabs_editors.setTabsClosable(True)
        self._tabs_editors.setMovable(True)

    def _connect(self):
        self._btn_graph_reload.pressed.connect(self.cb_reload_graphs)
        self._btn_help.pressed.connect(self.cb_help)
        self._action_new.triggered.connect(self.cb_new)
        self._action_open.triggered.connect(self.cb_open)
        self._action_save.triggered.connect(self.cb_save)
        self._action_build.triggered.connect(self.cb_build)
        self._tabs_editors.tabCloseRequested.connect(self._close_tag)

    def cb_help(self):
        self.cb_open(path=str((_pathlib.Path(__file__)/".."/"bsl"/"syntax").resolve()))
        return


    def cb_reload_graphs(self):
        from maya import cmds
        cmds.loadPlugin("bifrostGraph", qt=True)

        s_current = self._cbx_graph.currentText()

        sa_new = sorted(cmds.ls(type="bifrostGraphShape") + cmds.ls(type="bifrostBoard")) + ["New Graph...", "New Board..."]

        self._cbx_graph.clear()

        for i, s in enumerate(sa_new):
            self._cbx_graph.addItem(s, s if i < len(sa_new)-2 else (int("Graph" in s)-2))

        # self._cbx_graph.addItems(sa_new)
        if s_current in sa_new:
            self._cbx_graph.setCurrentIndex(sa_new.index(s_current))

    def keyPressEvent(self, event):
        if (event.modifiers() & _QtCore.Qt.ControlModifier) and (event.key() == _QtCore.Qt.Key_N):
            self.cb_new()
            return

        if (event.modifiers() & _QtCore.Qt.ControlModifier) and (event.key() == _QtCore.Qt.Key_Q):
            self.cb_close()
            return

        if (event.modifiers() & _QtCore.Qt.ControlModifier) and (event.key() == _QtCore.Qt.Key_O):
            self.cb_open()
            return

        if (event.modifiers() & _QtCore.Qt.ControlModifier) and (event.key() == _QtCore.Qt.Key_S):
            _QtCore.QTimer.singleShot(0, self.cb_save)
            return

        if (event.modifiers() & _QtCore.Qt.ControlModifier) and (event.key() in (_QtCore.Qt.Key_Return, _QtCore.Qt.Key_Enter)):
            _QtCore.QTimer.singleShot(0, self.cb_build)

        return super().keyPressEvent(event)

    def _add_editor_tab(self, d_file):
        if d_file is not None:
            path = _pathlib.Path(d_file["path"]).resolve().absolute()
            for tab in self._d_tabs.values():
                if tab.path() == path:
                    tab.set_active()
                    return

        s_id = _get_uuid()
        self._d_tabs[s_id] = _BSLEditorTab(s_id, d_file, parent=self)
        self._d_tabs[s_id].add_to_widget(self._tabs_editors)
        self._tabs_editors.setCurrentIndex(self._tabs_editors.count()-1)

    def _close_tag(self, index_or_uuid):
        if isinstance(index_or_uuid, int):
            index_or_uuid = self._tabs_editors.widget(index_or_uuid).objectName()

        tab = self._d_tabs[index_or_uuid]
        if not tab.is_modified():
            self._d_tabs[index_or_uuid].remove_from_widget()
            del self._d_tabs[index_or_uuid]
            return

        reply = _QtWidgets.QMessageBox()
        reply.setIcon(_QtWidgets.QMessageBox.Icon.Warning)
        reply.setWindowTitle("Save changes")
        reply.setText(f"Do you want to save changes made to '{tab.name()}'?")
        btn_save = reply.addButton("Save", _QtWidgets.QMessageBox.ButtonRole.YesRole)
        btn_dont = reply.addButton("Dont save", _QtWidgets.QMessageBox.ButtonRole.NoRole)
        btn_cancel = reply.addButton("Cancel", _QtWidgets.QMessageBox.ButtonRole.RejectRole)
        reply.setDefaultButton(btn_save)
        reply.setEscapeButton(btn_cancel)

        result = reply.exec()

        if result == 0:
            def _close():
                self._d_tabs[index_or_uuid].remove_from_widget()
                del self._d_tabs[index_or_uuid]

            self._d_tabs[index_or_uuid].set_active()
            self.cb_save(x_on_success=lambda: self._close_tag(index_or_uuid))
            return

        elif result == 1:
            # close without saving
            self._d_tabs[index_or_uuid].remove_from_widget()
            del self._d_tabs[index_or_uuid]

        elif result == 2:
            # dont close
            return

    def get_active_tab(self):
        if self._tabs_editors.currentWidget() is None:
            return
        return self._d_tabs[self._tabs_editors.currentWidget().objectName()]

    def cb_new(self):
        self._add_editor_tab(None)

    def cb_close(self):
        active_tab = self.get_active_tab()
        if active_tab is None:
            return False

        self._close_tag(active_tab.id())

    def cb_open(self, *args, path=""):
        file_path, _ = _QtWidgets.QFileDialog.getOpenFileName(self, "Open File", path)
        if file_path:
            try:
                with open(file_path, "r") as f:
                    content = f.read()
                file_name = _os.path.basename(file_path)
                ext = _os.path.splitext(file_path)[1].lower()
                language = "plaintext"
                if ext == ".py":
                    language = "python"
                elif ext in [".bf", ".bfl"]:
                    language = "bsl"
                fileData = {
                    "path": file_path,
                    "name": file_name,
                    "content": content,
                    "language": language
                }
                self._add_editor_tab(fileData)

            except Exception as e:
                _QtWidgets.QMessageBox.warning(self, "Error", "Failed to open file: " + str(e))

    def cb_save(self, x_on_success=lambda *args, **kwargs: None, x_on_failure=lambda *args, **kwargs: None):
        active_tab = self.get_active_tab()
        if active_tab is None:
            print("active tab is none")
            return

        web_view_active = active_tab.widget()

        def _cb_save(s_content, x_succeed, x_fail):
            if s_content is None:
                _QtWidgets.QMessageBox.warning(self, "Error", "Failed to retrieve editor content.")
                x_fail()
                return False

            tab = self.get_active_tab()

            if tab.path() is None:
                path, _ = _QtWidgets.QFileDialog.getSaveFileName(self, "Save File")

                if not path:
                    x_fail()
                    return False

                path = str(_pathlib.Path(path).absolute().resolve())
                current_paths = [str(tab.path()) for tab in self._d_tabs.values() if tab.path()]

                if path in current_paths:
                    _QtWidgets.QMessageBox.critical(self, "Error", "Path already open in another editor.")
                    x_fail()
                    return False

                tab.save_as(path=path, s_content=s_content)

            else:
                tab.save_as(path=tab.path(), s_content=s_content)

            x_succeed()
            return True

        event_loop = _QtCore.QEventLoop()

        def _cb(s_content):
            _cb_save(s_content=s_content, x_succeed=lambda: None, x_fail=lambda: None)
            event_loop.exit()

        # jfc qt...
        _QtCore.QTimer.singleShot(0, lambda: web_view_active.page().runJavaScript("getEditorContent();", 0, _cb))
        event_loop.exec_()

        # this should not be taking longer than 10 secs...
        i_max = 10
        while event_loop.isRunning() and i_max > 0:
            i_max -= 1
            time.sleep(1)

        if event_loop.isRunning():
            raise Exception("Something went pretty wrong...")

    def cb_build(self):
        method = self._cbx_method.currentText()
        target = self._cbx_graph.currentData()

        # save before execution
        self.cb_save()

        active_tab = self.get_active_tab()
        if active_tab is None:
            return

        from maya import cmds
        if method == "vnn":
            if target == -1:
                s_graph = cmds.createNode("bifrostGraphShape")
                self.cb_reload_graphs()

            elif target == -2:
                s_graph = cmds.createNode("bifrostBoard")
                self.cb_reload_graphs()

            else:
                s_graph = target

            self._cbx_graph.setCurrentText(s_graph)

            import BSL

            with BSL.Graph(s_graph, "/") as graph:
                result = BSL.Ast.run(active_tab.path())
                for x in result:
                    x.to_vnn(graph)

        else:
            raise NotImplementedError


def _getMayaMainWindow():
    from maya import OpenMayaUI as omui
    main_window_ptr = omui.MQtUtil.mainWindow()
    if main_window_ptr is not None:
        return _wrapInstance(int(main_window_ptr), _QtWidgets.QWidget)
    return None


def _create_dockable_editor():
    from maya import cmds
    from maya import OpenMayaUI as omui

    parent = _getMayaMainWindow()

    if cmds.workspaceControl("BSLEditor", exists=True):
        cmds.deleteUI("BSLEditor")
    cmds.workspaceControl("BSLEditor", label="BSL Editor", loadImmediately=True)
    ctrl = omui.MQtUtil.findControl("BSLEditor")

    dock_widget = _wrapInstance(int(ctrl), _QtWidgets.QWidget)
    if dock_widget.layout() is None:
        layout = _QtWidgets.QVBoxLayout(dock_widget)
    else:
        layout = dock_widget.layout()
    editor = _BSLEditor(dock_widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(editor)
    editor.show()
    return editor


def show_from_headless():
    qapp = _QtWidgets.QApplication()

    from maya import standalone
    standalone.initialize()

    editor = _BSLEditor()
    editor.show()
    editor.setFocus()
    _exec(qapp)


def show(b_dockable=True):
    if b_dockable:
        editor = _create_dockable_editor()
    else:
        editor = _BSLEditor()
        editor.show()

    editor.setFocus()

