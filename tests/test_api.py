import pytest

from src import MovieStorage
import main

def test_movies_persist(client, test_storage, uploaded_movies):
    storage = MovieStorage(test_storage.db_path)
    movies = storage.get()

    assert len(movies) == uploaded_movies["rows"]
    assert list(movies.columns) == uploaded_movies["column_names"]

    expected_titles = [
        "Movie A", "Movie B", "Movie B", "Movie C", "Movie D", "Movie D",
        "Movie E", "Movie F", "Movie G", "Movie H", "Movie I", "Movie J",
        "Movie K", "Movie L", "Movie M", "Movie N", "Movie O", "Movie P",
        "Movie Q", "Movie R"
    ]
    assert movies["title"].tolist() == expected_titles

    storage_ids = [row["id"] for row in storage.select_columns(["title"], 100)]
    response = client.get("/movies?limit=100")
    with_ids = [row["id"] for row in response.json()["data"]]
    # get is not allowed to return IDs with the data, so I do not think that this test should happen
    assert storage_ids == with_ids == list(range(1, 21))


def test_cache_and_processing(client, uploaded_movies, processing_body):
    response_100 = client.get("/movies?limit=100")
    assert response_100.status_code == 200
    assert main.cache.get(100) == response_100.json()

    response_1 = client.get("/movies?limit=1")
    assert response_1.status_code == 200
    assert main.cache.get(1) == response_1.json()

    response_100_again = client.get("/movies?limit=100")
    assert response_100_again.status_code == 200
    assert response_100_again.json() == response_100.json()

    response = client.post("/movies/process", json=processing_body)
    assert response.status_code == 200
    report = response.json()
    assert report["validation_rows_removed"] == 0
    assert report["cleaning_report"]["rows_before"] == 20
    assert report["cleaning_report"]["rows_after"] == 16
    assert report["cleaning_report"]["rows_removed"] == 4

    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    response = client.get("/movies?limit=100")
    assert response.status_code == 200
    movies = response.json()
    assert movies["total_rows"] == 16

    expected_titles = [
        "Movie A", "Movie B", "Movie C", "Movie D", "Movie E", "Movie F",
        "Movie G", "Movie H", "Movie I", "Movie J", "Movie K", "Movie L",
        "Movie M", "Movie N", "Movie O", "Movie P",
    ]

    assert [row["title"] for row in movies["data"]] == expected_titles
    assert [row["id"] for row in movies["data"]] == list(range(1, 17))

    assert main.cache.get(100) == movies


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    response_original = client.get("/movies?limit=100")
    assert response_original.status_code == 200

    monkeypatch.setattr(main.storage, "select_columns", lambda *args, **kwargs: pytest.fail("select_columns was called"))
    monkeypatch.setattr(main.storage, "count_movies", lambda *args, **kwargs: pytest.fail("count_movies was called"))

    response = client.get("/movies?limit=100")
    assert response.status_code == 200
    assert response.json() == response_original.json()
    

