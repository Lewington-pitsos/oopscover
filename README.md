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


## Elastic Beanstalk

Create the app with

`eb init -p python-3.10 ouchmate --region ap-southeast-2`

create elastic beanstalk environment with

`eb create flask-env -i c4.large`

Destroy the environment 

`eb terminate flask-env`