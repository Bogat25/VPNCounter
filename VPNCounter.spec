from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

datas, binaries, hiddenimports = collect_all('faster_whisper')
for package in ('nvidia.cublas', 'nvidia.cudnn', 'nvidia.cuda_nvrtc'):
    binaries += collect_dynamic_libs(package)

analysis = Analysis(
    ['src/vpn_counter/__main__.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=['tkinter', 'matplotlib', 'IPython', 'torch', 'pytest', '_pytest'],
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name='VPNCounter',
    console=False,
    upx=False,
)
collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    name='VPNCounter',
    upx=False,
)

# A separate, self-contained download using the same analyzed dependencies.
portable = EXE(
    archive,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name='VPNCounter-portable',
    console=False,
    upx=False,
)
