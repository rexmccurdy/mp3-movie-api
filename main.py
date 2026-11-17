import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import (
    DatasetInfo, 
    MovieStorage, 
    HealthResponse, 
    ProcessConfig, 
    MovieStorage,
    MovieUploadInfo,
    MovieDataResponse,
    MovieProcessingReport,
    ProcessingReport,
    MovieCache,
    setup_logging, 
    log_requests
)
from src.storage import MOVIE_COLUMNS
from data_pipeline import create_cleaning_report, process_data, validate_dataframe


setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
storage = MovieStorage()
cache = MovieCache()

@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok", version="1.0.0")


@app.post("/upload", response_model=MovieUploadInfo)
async def upload_movies(file: UploadFile = File(...)):
    if Path(file.filename or "").suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        logger.warning(f"Failed to read CSV file: {file.filename}")
        raise HTTPException(status_code=400, detail="Invalid CSV file")

    if set(df.columns) != set(MOVIE_COLUMNS) or df.empty:
        raise HTTPException(status_code=400, detail="Columns do not match or no data is present")

    df = df[MOVIE_COLUMNS]

    storage.save(df)
    cache.invalidate()

    logger.info(f"Saved {len(df)} rows from {file.filename}")

    return MovieUploadInfo(
        filename=file.filename,
        rows=len(df),
        columns=len(df.columns),
        column_names=df.columns.tolist()
    )

    

@app.get("/movies")
def get_dataset(limit: int = Query(default=100, ge=1)):

    cached = cache.get(limit)
    if cached is not None:
        logger.info(f"Cache HIT, limit: {limit}")
        return cached
    df = storage.get()
    df.insert(0, "id", range(1, len(df) + 1))
    
    records = json.loads(df.head(limit).to_json(orient="records"))
    response = {"data": records, "total_rows": len(df)}
    cache.set(limit, response)
    logger.info(f"Got {len(df)} rows from storage")
    return response



@app.get("/movies/search", response_model=list[dict])
def query_movies(
    columns: list[str] = Query(default=["title"]),
    min_rating: float = Query(default=0, ge=0, le=10),
    limit: int = Query(default=100, ge=1)
):
    try:
        movies = storage.query_movies(columns, min_rating, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    logger.info(f"Returned {len(movies)} rows for selected columns: {columns}")
    return movies


@app.post(
    "/movies/process",
    response_model=MovieProcessingReport
)
def process_movies(config: ProcessConfig):
    df = storage.get()
    if df.empty:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    config_dict = config.model_dump()
    for col in config_dict["validation"]["required_columns"]:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Missing required column: {col}")

    try:
        pre_validation = df.copy()
        validation = config_dict["validation"]
        df = validate_dataframe(df, required_columns=validation["required_columns"], numeric_columns=validation["numeric_columns"])     
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    post_validation = df.copy()
    try:
        df = process_data(df, config_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    cleaning_report = create_cleaning_report(post_validation, df)

    storage.save(df)
    cache.invalidate()

    logger.info(f"Dataset processed, "
                f"{len(post_validation) - len(df)} rows removed, "
                f"Cleaning report: {cleaning_report}")
    return MovieProcessingReport(
        validation_rows_removed=len(pre_validation) - len(post_validation),
        cleaning_report=cleaning_report
    )
