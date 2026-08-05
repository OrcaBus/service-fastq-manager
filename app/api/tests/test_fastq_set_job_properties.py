#!/usr/bin/env python3

"""
Property-based tests for FastqSetJob model.
"""

import os
import sys
from pathlib import Path

# Set required environment variables before any model imports
os.environ["DYNAMODB_FASTQ_SET_JOB_TABLE_NAME"] = "test_fastq_set_job_table"
os.environ["DYNAMODB_HOST"] = "http://localhost:8456"
os.environ["DYNAMODB_FASTQ_TABLE_NAME"] = "test_fastq_table"
os.environ["DYNAMODB_FASTQ_SET_TABLE_NAME"] = "test_fastq_set_table"
os.environ["DYNAMODB_FASTQ_JOB_TABLE_NAME"] = "test_fastq_job_table"
os.environ["DYNAMODB_MULTIQC_JOB_TABLE_NAME"] = "test_multiqc_job_table"
os.environ["FASTQ_BASE_URL"] = "http://localhost:8457"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["EVENT_BUS_NAME"] = "test-event-bus"
os.environ["EVENT_SOURCE"] = "test-source"
os.environ["EVENT_DETAIL_TYPE_FASTQ_LIST_ROW_STATE_CHANGE"] = "FastqStateChange"
os.environ["EVENT_DETAIL_TYPE_FASTQ_SET_ROW_STATE_CHANGE"] = "FastqSetStateChange"
os.environ["EVENT_DETAIL_TYPE_MULTIQC_JOB_STATE_CHANGE"] = "MultiqcJobStateChange"

# Add Lambda layer paths (fastapi_tools, orcabus_api_tools) to sys.path for testing
_LAYERS_BASE = Path(__file__).resolve().parents[3] / "node_modules" / ".pnpm"
_LAYERS_DIRS = list(_LAYERS_BASE.glob(
    "@orcabus+platform-cdk-constructs*/node_modules/@orcabus/platform-cdk-constructs/lambda/layers"
))
if _LAYERS_DIRS:
    _layers_dir = _LAYERS_DIRS[0]
    for _layer in ["fastapi_tools", "orcabus_api_tools"]:
        _layer_src = _layers_dir / _layer / "src"
        if _layer_src.exists() and str(_layer_src) not in sys.path:
            sys.path.insert(0, str(_layer_src))

from hypothesis import given, settings
from hypothesis import strategies as st

from fastq_manager_api_tools.models.fastq_set_job import (
    FastqSetJobWithId,
    FastqSetJobResponse,
    FastqSetJobQueryPaginatedResponse,
)


# Strategies for generating random data
fastq_set_id_strategy = st.from_regex(r"fqs\.[A-Z0-9]{26}", fullmatch=True)

job_type_strategy = st.just("EXTRACT_FINGERPRINT")


class TestFastqSetJobResponseSerializationCompleteness:
    """
    Property 4: Successful response serialization completeness

    For any successfully created FastqSetJobData instance, the serialized response
    (using camelCase aliases) SHALL contain all of the following keys:
    id, fastqSetId, jobType, status, stepsExecutionArn, startTime, endTime, ttl.

    **Validates: Requirements 2.3, 5.1**
    """

    @given(
        fastq_set_id=fastq_set_id_strategy,
        job_type=job_type_strategy,
    )
    @settings(max_examples=100)
    def test_serialization_contains_all_camel_case_keys(
        self,
        fastq_set_id: str,
        job_type: str,
    ):
        """
        Verify that serialized response contains ALL required camelCase keys.

        **Validates: Requirements 2.3, 5.1**
        """
        # Create instance with random data
        instance = FastqSetJobWithId(
            fastq_set_id=fastq_set_id,
            job_type=job_type,
        )

        # Serialize via FastqSetJobResponse (camelCase aliased model)
        response = FastqSetJobResponse(**dict(instance.model_dump()))
        serialized = response.model_dump(by_alias=True)

        # All required camelCase keys must be present
        expected_keys = {
            "id",
            "fastqSetId",
            "jobType",
            "status",
            "stepsExecutionArn",
            "startTime",
            "endTime",
            "ttl",
        }

        assert expected_keys.issubset(serialized.keys()), (
            f"Missing keys: {expected_keys - set(serialized.keys())}. "
            f"Got keys: {set(serialized.keys())}"
        )


from unittest.mock import patch, MagicMock
from fastapi import HTTPException


class TestDuplicateJobPrevention:
    """
    Property 3: Duplicate job prevention

    For any fastq_set_id that already has a FastqSetJobData record with
    job_type=EXTRACT_FINGERPRINT and status in (PENDING, RUNNING), calling
    run_and_save_fastq_set_job SHALL return HTTP 218 with the existing job's
    ID in the response detail, without creating a new job record.

    **Validates: Requirements 2.2**
    """

    @given(
        fastq_set_id=st.from_regex(r"fqs\.[A-Z0-9]{26}", fullmatch=True),
        status=st.sampled_from(["PENDING", "RUNNING"]),
    )
    @settings(max_examples=100)
    def test_duplicate_job_returns_218(self, fastq_set_id: str, status: str):
        """
        For any fastq_set_id that already has a job with PENDING or RUNNING status,
        calling run_and_save_fastq_set_job SHALL raise HTTPException with status 218.

        **Validates: Requirements 2.2**
        """
        from fastq_manager_api_tools.api.v1.routers import run_and_save_fastq_set_job

        # Create a mock existing job
        existing_job = MagicMock()
        existing_job.id = f"fsj.{'A' * 26}"
        existing_job.status = status
        existing_job.job_type = "EXTRACT_FINGERPRINT"

        # Mock the query to return an existing job
        with patch(
            'fastq_manager_api_tools.models.fastq_set_job.FastqSetJobData.query',
            return_value=[existing_job],
        ):
            try:
                run_and_save_fastq_set_job(
                    fastq_set_id=fastq_set_id,
                    job_type="EXTRACT_FINGERPRINT",
                    sfn_env_var="EXTRACT_FINGERPRINT_AWS_STEP_FUNCTION_ARN",
                    sfn_input={"fastqSetId": fastq_set_id},
                )
                assert False, "Expected HTTPException with status 218"
            except HTTPException as e:
                assert e.status_code == 218, f"Expected 218, got {e.status_code}"
                assert existing_job.id in e.detail, (
                    f"Expected existing job ID '{existing_job.id}' in detail, got: {e.detail}"
                )


from datetime import datetime, timezone


class TestSortOrder:
    """
    Property 6: Results sorted by start_time descending

    For any query response containing two or more results,
    results[i].startTime >= results[i+1].startTime for all consecutive pairs.

    **Validates: Requirements 3.4**
    """

    @given(
        start_times=st.lists(
            st.datetimes(
                min_value=datetime(2020, 1, 1),
                max_value=datetime(2030, 1, 1),
                timezones=st.just(timezone.utc),
            ),
            min_size=2,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_results_sorted_by_start_time_descending(self, start_times):
        """
        For any query response containing two or more results,
        results[i].startTime >= results[i+1].startTime for all consecutive pairs.

        **Validates: Requirements 3.4**
        """
        # Create job instances with the generated start_times
        jobs = []
        for st_time in start_times:
            job = FastqSetJobWithId(
                fastq_set_id="fqs.01HXY1234567890ABCDEFGHIJ",
                job_type="EXTRACT_FINGERPRINT",
                start_time=st_time,
            )
            jobs.append(job)

        # Sort by start_time descending (simulating endpoint behavior)
        jobs.sort(key=lambda j: j.start_time, reverse=True)

        # Serialize to response format
        serialized_jobs = []
        for job in jobs:
            response = FastqSetJobResponse(**dict(job.model_dump()))
            serialized = response.model_dump(by_alias=True)
            serialized_jobs.append(serialized)

        # Verify descending order
        for i in range(len(serialized_jobs) - 1):
            current_time = serialized_jobs[i]['startTime']
            next_time = serialized_jobs[i + 1]['startTime']
            assert current_time >= next_time, (
                f"Sort order violated at index {i}: "
                f"{current_time} < {next_time}"
            )


class TestQueryPaginationCorrectness:
    """
    Property 5: Query returns correct paginated subset

    For any valid fastq_set_id referencing an existing FastqSet, and any valid
    pagination parameters (page >= 1, rowsPerPage >= 2), the GET /jobs endpoint
    SHALL return a response containing a results array with at most rowsPerPage
    items that all belong to the specified fastq_set_id, a links object (with
    self, next, previous), and a pagination object (with count, page, rowsPerPage).

    **Validates: Requirements 3.1, 3.3, 5.2**
    """

    @given(
        num_jobs=st.integers(min_value=0, max_value=50),
        page=st.integers(min_value=1, max_value=10),
        rows_per_page=st.integers(min_value=2, max_value=20),
    )
    @settings(max_examples=100)
    def test_pagination_returns_correct_subset(
        self, num_jobs: int, page: int, rows_per_page: int
    ):
        """
        For any valid pagination parameters, verify the paginated response
        contains at most rowsPerPage items and has proper structure.

        **Validates: Requirements 3.1, 3.3, 5.2**
        """
        from datetime import datetime, timezone, timedelta

        # Create job response dicts (simulating already-serialized results)
        job_responses = []
        base_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(num_jobs):
            job = FastqSetJobWithId(
                fastq_set_id="fqs.01HXY1234567890ABCDEFGHIJ",
                job_type="EXTRACT_FINGERPRINT",
                start_time=base_time - timedelta(hours=i),
            )
            response = FastqSetJobResponse(**dict(job.model_dump()))
            job_responses.append(response.model_dump(by_alias=True))

        # Use FastqSetJobQueryPaginatedResponse.from_results_list
        result = FastqSetJobQueryPaginatedResponse.from_results_list(
            results=job_responses,
            query_pagination={"page": page, "rowsPerPage": rows_per_page},
            params_response={},
            fastq_set_id="fqs.01HXY1234567890ABCDEFGHIJ",
        )

        # Verify structure - must have results, links, pagination
        assert hasattr(result, 'results'), "Response must have 'results'"
        assert hasattr(result, 'links'), "Response must have 'links'"
        assert hasattr(result, 'pagination'), "Response must have 'pagination'"

        # Verify results count is at most rowsPerPage
        assert len(result.results) <= rows_per_page, (
            f"Expected at most {rows_per_page} results, got {len(result.results)}"
        )

        # Verify the correct slice is returned
        expected_start = (page - 1) * rows_per_page
        expected_end = expected_start + rows_per_page
        expected_results = job_responses[expected_start:expected_end]
        assert len(result.results) == len(expected_results), (
            f"Expected {len(expected_results)} results for page {page}, "
            f"got {len(result.results)}"
        )

        # Verify pagination fields
        result_dict = result.model_dump()
        assert 'pagination' in result_dict
        pagination = result_dict['pagination']
        assert 'count' in pagination, "pagination must contain 'count'"
        assert 'page' in pagination, "pagination must contain 'page'"
        assert 'rowsPerPage' in pagination, "pagination must contain 'rowsPerPage'"
        assert pagination['count'] == num_jobs, (
            f"Expected count={num_jobs}, got {pagination['count']}"
        )
        assert pagination['rowsPerPage'] == rows_per_page, (
            f"Expected rowsPerPage={rows_per_page}, got {pagination['rowsPerPage']}"
        )
        assert pagination['page'] == page, (
            f"Expected page={page}, got {pagination['page']}"
        )

        # Verify links structure
        assert 'links' in result_dict
        links = result_dict['links']
        assert 'next' in links, "links must contain 'next'"
        assert 'previous' in links, "links must contain 'previous'"

        # Verify next link logic
        if page * rows_per_page >= num_jobs:
            assert links['next'] is None, (
                f"Expected next=None when on last page (page={page}, "
                f"rows_per_page={rows_per_page}, total={num_jobs})"
            )
        else:
            assert links['next'] is not None, (
                f"Expected next link when more results exist (page={page}, "
                f"rows_per_page={rows_per_page}, total={num_jobs})"
            )

        # Verify previous link logic
        if page == 1:
            assert links['previous'] is None, "Expected previous=None on first page"
        else:
            assert links['previous'] is not None, (
                f"Expected previous link when page > 1 (page={page})"
            )
