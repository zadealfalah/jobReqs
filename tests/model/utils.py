import ray

from src import predict


def get_label(text, predictor):
    sample_ds = ray.data.from_items([{"description": text, "tag": "other"}])
    results = predict.predict_proba(ds=sample_ds, predictor=predictor)
    return results[0]["prediction"]