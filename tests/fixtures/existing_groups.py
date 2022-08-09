import boto3
import os
import pytest
from moto import mock_iam

@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"

@pytest.fixture(scope='function')
def iam_client(aws_credentials):
    with mock_iam():
        conn = boto3.client("iam", region_name="us-east-1")
        yield conn
