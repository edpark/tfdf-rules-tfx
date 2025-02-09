# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Cloud Function to be triggered by Pub/Sub."""

import os
import json
import logging
from kfp.v2.google.client import AIPlatformClient
from google.cloud import storage
import base64


def trigger_pipeline(event, context):

    project = os.getenv("PROJECT")
    region = os.getenv("REGION")
    gcs_pipeline_file_location_env = os.getenv("GCS_PIPELINE_FILE_LOCATION")

    if not project:
        raise ValueError("Environment variable PROJECT is not set.")
    if not region:
        raise ValueError("Environment variable REGION is not set.")

    data = base64.b64decode(event["data"]).decode("utf-8")
    logging.info(f"Event data: {data}")

    parameter_values = json.loads(data)

    if 'gcs_pipeline_file_location' not in parameter_values and not gcs_pipeline_file_location_env:
        raise ValueError("GCS_PIPELINE_FILE_LOCATION is not set in either message parameter_values or environment variable.")
    
    if 'gcs_pipeline_file_location' in parameter_values:
        gcs_pipeline_file_location = parameter_values.pop('gcs_pipeline_file_location')
    else:
        gcs_pipeline_file_location = gcs_pipeline_file_location_env

    storage_client = storage.Client()

    path_parts = gcs_pipeline_file_location.replace("gs://", "").split("/")
    bucket_name = path_parts[0]
    blob_name = "/".join(path_parts[1:])

    bucket = storage_client.bucket(bucket_name)
    blob = storage.Blob(bucket=bucket, name=blob_name)

    if not blob.exists(storage_client):
        raise ValueError(f"{gcs_pipeline_file_location} does not exist.")

    api_client = AIPlatformClient(project_id=project, region=region)

    logging.info(f"parameter_values: {parameter_values}")

    response = api_client.create_run_from_job_spec(
        job_spec_path=gcs_pipeline_file_location, parameter_values=parameter_values
    )

    logging.info(response)
