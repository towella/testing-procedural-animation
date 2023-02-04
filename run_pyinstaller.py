import PyInstaller.__main__

PyInstaller.__main__.run([
    'code/main.py',
    '--onefile',
    '--noconsole',
    '--debug=imports'
    #'--add-binary=rooms:rooms'
    #'--add-data='
])

# https://github.com/retifrav/generate-iconset/blob/master/README.md
# download generate-iconset package
# icon image must be 512x512px or 1024x1024px at 300dpi for use
# generate-iconset path/to/image/app_icon.png --use-sips
# path should be from root folder not relative path :)

# main.spec > datas = [('assets, assets')] > assets become part of app, they are not required to be pasted into package
# *!works!* :)
