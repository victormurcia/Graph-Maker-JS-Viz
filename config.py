from dotenv import load_dotenv
import os

load_dotenv()

ANNOTATION_DIR = os.path.normpath(os.getenv("ANNOTATION_DIR"))
PARQUET_PATH   = os.path.normpath(os.getenv("PARQUET_PATH"))
DS_PATH        = os.path.join(ANNOTATION_DIR, "ds_annotations.parquet")
CL_PATH        = os.path.join(ANNOTATION_DIR, "clinician_annotations.parquet")