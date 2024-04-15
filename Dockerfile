FROM python:3.11 as deps 

WORKDIR /src/keanu

# Ongoing issue with PyYAML which is pulled in by one of the deps
# https://github.com/yaml/pyyaml/issues/601
# A workaround:
# https://github.com/yaml/pyyaml/issues/724#issuecomment-2045560179

RUN pip install "cython<3.0.0" pipenv build setuptools-pipfile && \
    pip install --no-build-isolation pyyaml==5.3.1

COPY Pipfile Pipfile.lock README.md setup.py /src/keanu/

RUN pipenv --python /usr/local/bin/python install 

COPY keanu /src/keanu/keanu

# This builds a wheen without deps...
RUN pwd && ls -l && python -m build -w -n && pip install dist/*.whl

# build options:
#  --wheel, -w           build a wheel (disables the default behavior)
#  --skip-dependency-check, -x
#                        do not check that build dependencies are installed
#  --no-isolation, -n    disable building the project in an isolated virtual environment. Build dependencies must be installed
#                        separately when this option is used
# with no options, build would error out with Pipfile not found, despite the file present in /app
