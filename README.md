# OuchCover

## Installing

Make a virtualenv with puython 3.10, activate it and then 

`pip install --upgrade pip`
`pip install 'farm-haystack[all]' ## or 'all-gpu' for the GPU-enabled dependencies`

`pip install -r requirements.txt`

You will also need to 

`cd frontend`
`pip install -e .`

since this installs `ui` as a package.

## Running

start the backend with

`python serve.py`

and then the frontend with

`cd frontend`
`streamlit run ui/webapp.py`