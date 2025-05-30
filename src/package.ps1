#Remove-Item -LiteralPath "build" -Force -Recurse
#Remove-Item -LiteralPath "dist" -Force -Recurse
#pyinstaller.exe  --icon ..\spec\itubego-dl.ico --onefile itubego-dl.py
#python -m nuitka --standalone  itubego-dl.py

# 打包前，如果项目中有独立python开发环境如".venv3_8", 优先使用独立环境，执行".venv3_8/Scripts/activate"

param(
    [string]$name
)

if (Test-Path -Path "build"){
  Remove-Item -LiteralPath "build" -Force -Recurse
}
if (Test-Path -Path "dist"){
  Remove-Item -LiteralPath "dist" -Force -Recurse
}

if($name -ieq "oneconv") {
  # pyinstaller.exe  --icon ..\spec\oneconv-dl.ico --onefile --name oneconv-dl itubego-dl.py -p ..\src
  # pyarmor gen --pack .\dist\oneconv-dl.exe -r itubego-dl.py .\my_get
  pyinstaller.exe  --icon ..\spec\oneconv-dl.ico --name oneconv-dl itubego-dl.py -p ..\src
  pyarmor gen --pack .\dist\oneconv-dl\oneconv-dl.exe -r itubego-dl.py .\my_get
} elseif($name -ieq "ultconv") {
  # pyinstaller.exe  --icon ..\spec\ultconv-dl.ico --onefile --name ultconv-dl itubego-dl.py -p ..\src
  # pyarmor gen --pack .\dist\ultconv-dl.exe -r itubego-dl.py .\my_get
  pyinstaller.exe  --icon ..\spec\ultconv-dl.ico --name ultconv-dl itubego-dl.py -p ..\src
  pyarmor gen --pack .\dist\ultconv-dl\ultconv-dl.exe -r itubego-dl.py .\my_get
} else {
  # pyinstaller.exe  --icon ..\spec\itubego-dl.ico --onefile itubego-dl.py -p ..\src
  # pyarmor gen --pack .\dist\itubego-dl.exe -r itubego-dl.py .\my_get
  pyinstaller.exe  --icon ..\spec\itubego-dl.ico itubego-dl.py -p ..\src
  pyarmor gen --pack .\dist\itubego-dl\itubego-dl.exe -r itubego-dl.py .\my_get
}


