# build.spec
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('PIL')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas + [('assets', 'assets')],
    hiddenimports=hiddenimports + [
        'ui.dialogs',
        'ui.gradient_window',
        'tasks.topic_upload',
        'utils.file_utils'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='EEP Topic Upload Tool',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          icon='assets\\EEP_512_512.ico')
