# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Recolectar submódulos y archivos de datos de scipy
hiddenimports = collect_submodules('scipy')
datas = collect_data_files('scipy')

a = Analysis(
    ['charly.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tk', 'test'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='charly',
    debug=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='charly',
    onefile=True,  # Opción para empaquetar en un solo archivo
)
