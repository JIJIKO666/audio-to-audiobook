# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('converter.py', '.'),
        ('i18n.py', '.'),
        ('theme.py', '.'),
        ('utils.py', '.'),
        ('scanner.py', '.'),
        ('workers.py', '.'),
        ('main.py', '.'),
        ('ui', 'ui'),
    ],
    hiddenimports=[
        'ui.widgets', 'ui.dialogs', 'ui.drop_zone',
        'ui.track_table', 'ui.cover_widget', 'ui.section', 'ui.main_window',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Audiobook Maker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Audiobook Maker',
)
app = BUNDLE(
    coll,
    name='Audiobook Maker.app',
    icon='img/icon.icns',
    bundle_identifier='com.audiobook.maker',
)
