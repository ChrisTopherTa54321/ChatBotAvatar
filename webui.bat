call webui-user.bat

IF NOT EXIST %VENV_DIR% (
    echo "Creating new virtual environment %VENV_DIR%"
    %PYTHON% -m venv %VENV_DIR%
)
call %VENV_DIR%/scripts/activate.bat

IF NOT EXIST setup_done (
    %PYTHON% setup.py
    echo NUL > setup_done
    echo "setup.py has been ran. To run it again delete the 'setup_done' file"
)

%PYTHON% main.py %COMMANDLINE_ARGS%

deactivate