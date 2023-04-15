. webui-user.sh

if [ ! -e $VENV_DIR ]
then
    echo "Creating new virtual environment $VENV_DIR"
    $PYTHON -m venv $VENV_DIR
fi

. $VENV_DIR/bin/activate

if [ ! -e setup_done ]
then
    $PYTHON setup.py
    touch setup_done
    echo "setup.py has been ran. To run it again delete the 'setup_done' file"
fi

$PYTHON main.py $COMMANDLINE_ARGS

deactivate