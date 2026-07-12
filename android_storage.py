import os

from kivy.utils import platform

if platform != "android":
    raise RuntimeError("android_storage.py solo puede usarse en Android")

from jnius import autoclass, PythonJavaClass, java_method

Uri = autoclass("android.net.Uri")
File = autoclass("java.io.File")
FileInputStream = autoclass("java.io.FileInputStream")


from android.activity import bind, unbind

PythonActivity = autoclass("org.kivy.android.PythonActivity")
Intent = autoclass("android.content.Intent")
DocumentsContract = autoclass("android.provider.DocumentsContract")
PreferenceManager = autoclass("android.preference.PreferenceManager")

activity = PythonActivity.mActivity

PREF_KEY = "download_tree_uri"
REQUEST_CODE = 5001


class AndroidStorage:

    def __init__(self):
        self._callback = None

    def get_saved_uri(self):
        prefs = PreferenceManager.getDefaultSharedPreferences(activity)
        return prefs.getString(PREF_KEY, None)

    def has_folder(self):
        return self.get_saved_uri() is not None
    
    def get_tree_uri(self):
        uri = self.get_saved_uri()

        if uri is None:
            return None

        return Uri.parse(uri)

    def choose_folder(self, callback=None):
        """
        callback(uri_string)
        """

        self._callback = callback

        intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE)

        intent.addFlags(
            Intent.FLAG_GRANT_READ_URI_PERMISSION
            | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
            | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
            | Intent.FLAG_GRANT_PREFIX_URI_PERMISSION
        )

        bind(on_activity_result=self._on_activity_result)

        activity.startActivityForResult(intent, REQUEST_CODE)

    def _on_activity_result(self, requestCode, resultCode, intent):

        if requestCode != REQUEST_CODE:
            return

        unbind(on_activity_result=self._on_activity_result)

        if intent is None:
            return

        uri = intent.getData()

        if uri is None:
            return

        flags = (
            Intent.FLAG_GRANT_READ_URI_PERMISSION
            | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        )

        activity.getContentResolver().takePersistableUriPermission(
            uri,
            flags
        )

        prefs = PreferenceManager.getDefaultSharedPreferences(activity)

        prefs.edit().putString(
            PREF_KEY,
            uri.toString()
        ).apply()

        if self._callback:
            self._callback(uri.toString())

    def save_file(self, local_path, mime_type):

        tree_uri = self.get_tree_uri()

        if tree_uri is None:
            raise RuntimeError("No hay carpeta seleccionada")

        resolver = activity.getContentResolver()

        tree_doc_id = DocumentsContract.getTreeDocumentId(tree_uri)

        parent_uri = DocumentsContract.buildDocumentUriUsingTree(
            tree_uri,
            tree_doc_id
        )

        filename = os.path.basename(local_path)

        new_uri = DocumentsContract.createDocument(
            resolver,
            parent_uri,
            mime_type,
            filename
        )

        if new_uri is None:
            raise RuntimeError("No se pudo crear el archivo")

        out_stream = resolver.openOutputStream(new_uri)

        in_stream = FileInputStream(File(local_path))

        buffer = bytearray(65536)

        while True:

            read = in_stream.read(buffer)

            if read == -1:
                break

            out_stream.write(buffer, 0, read)

        in_stream.close()
        out_stream.close()

        return new_uri.toString()
    
    def save_and_delete(self, local_path, mime_type):

        uri = self.save_file(local_path, mime_type)

        try:
            os.remove(local_path)
        except Exception as e:
            print("No se pudo borrar el temporal:", e)

        return uri