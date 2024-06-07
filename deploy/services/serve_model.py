import os
import subprocess
import sys

sys.path.append(".")

from src.config import MODEL_REGISTRY
from src.serve import ModelDeployment

# May change s3 bucket used, if so be sure to update here to not break!
github_username = os.environ.get("GITHUB_USERNAME")
subprocess.check_output(["aws", "s3", "cp", f"s3://jobclassifier/{github_username}/mlflow", str(MODEL_REGISTRY), "--recursive"])
subprocess.check_output(["aws", "s3", "cp", f"s3://jobclassifier/{github_username}/results/", "./", "--recursive"])

# Entrypoint
run_id = [line.strip() for line in open("run_id.txt")][0]
entrypoint = ModelDeployment.bind(run_id=run_id, threshold=0.5)