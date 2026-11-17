# MP3 Persistent Storage and Caching

This API gives the user an interface where they can upload, view, and process movie dataset using the pipeline created in MP1 and a given configuration. Movie data will be saved in a SQL database and caching will be used to minimize queries.

## Description

This program uses uvicorn and FastAPI to run the API application and connect endpoints.

The user can get the health of the program, upload and store a .csv movie data set, retrieve stored datasets, and process a dataset based on a given configuration (json format). The processing behind the data is done by the previously established mp1 pipeline.

This data will be stored in a database, persisting across sessions. Recent queries in /movies will be cached for 90 seconds, minimizing the workload of repeated queries.

## Use

Packages used are listed in requirements.txt.

To launch the application run:

>python -m uvicorn main:app --reload

and then go to http://127.0.0.1:8000/docs to try out the functions.

Upload a file at "/upload" to update the database, then view at "/movies" or "/movies/search". "/movies/process" can be used to process all movies in the database simultaneously.